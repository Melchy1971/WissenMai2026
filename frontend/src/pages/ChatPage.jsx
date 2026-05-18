import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { createChatSession, getChatSession, getChatSessions, postChatMessage } from '../api/chat.js';
import { createRequestCoordinator } from '../api/requestCoordinator.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { ChatComposer } from '../components/chat/ChatComposer.jsx';
import { ChatMessageThread } from '../components/chat/ChatMessageThread.jsx';
import { ChatSessionList } from '../components/chat/ChatSessionList.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { mapChatSessionDetail, mapChatSessionSummary, mapError, mapPostedChatResponse } from '../view-models/mappers.js';

export function ChatPage() {
  const navigate = useNavigate();
  const { id: activeSessionId } = useParams();
  const { token, active_workspace_id: workspaceId, isAuthReady } = useAuth();

  const [sessionsState, setSessionsState] = useState({ status: 'loading', items: [], error: null });
  const [detailState, setDetailState] = useState({ status: 'idle', item: null, error: null });
  const [titleInput, setTitleInput] = useState('');
  const [questionInput, setQuestionInput] = useState('');
  const prevWorkspaceIdRef = useRef(workspaceId);
  const requestContextRef = useRef({ authToken: '', workspaceId: '' });
  const requestCoordinatorRef = useRef(null);
  const chatWriteInFlightRef = useRef(false);

  requestContextRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!requestCoordinatorRef.current) {
    requestCoordinatorRef.current = createRequestCoordinator({
      getContext: () => requestContextRef.current,
    });
  }

  // Rule 6: navigate away from session-specific URL on workspace switch so the
  // detail load effect gets activeSessionId = undefined and resets detailState.
  useEffect(() => {
    if (prevWorkspaceIdRef.current === workspaceId) return;
    prevWorkspaceIdRef.current = workspaceId;
    requestCoordinatorRef.current.cancelAll();
    chatWriteInFlightRef.current = false;
    setTitleInput('');
    setQuestionInput('');
    setSessionsState({ status: 'loading', items: [], error: null });
    setDetailState({ status: 'idle', item: null, error: null });
    navigate('/chat', { replace: true });
  }, [workspaceId, navigate]);

  useEffect(() => {
    if (!isAuthReady) {
      setSessionsState({ status: 'loading', items: [], error: null });
      return () => {
        requestCoordinatorRef.current.cancel('chat:sessions');
      };
    }

    async function loadSessions() {
      const ticket = requestCoordinatorRef.current.begin('chat:sessions');
      setSessionsState({ status: 'loading', items: [], error: null });
      try {
        const response = await getChatSessions(
          { limit: 20, offset: 0 },
          { signal: ticket.signal, correlationId: ticket.correlationId },
        );
        if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
        const items = response.map(mapChatSessionSummary);
        setSessionsState({ status: 'success', items, error: null });
        if (!activeSessionId && items.length > 0) {
          navigate(`/chat/${items[0].id}`, { replace: true });
        }
      } catch (error) {
        if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
        setSessionsState({ status: 'error', items: [], error: mapError(error) });
      } finally {
        requestCoordinatorRef.current.complete(ticket);
      }
    }

    loadSessions();
    return () => {
      requestCoordinatorRef.current.cancel('chat:sessions');
    };
  }, [activeSessionId, navigate, workspaceId, isAuthReady]);

  useEffect(() => {
    if (!isAuthReady) {
      setDetailState({ status: 'loading', item: null, error: null });
      return () => {
        requestCoordinatorRef.current.cancel('chat:detail');
      };
    }
    if (!activeSessionId) {
      setDetailState({ status: 'idle', item: null, error: null });
      return () => {
        requestCoordinatorRef.current.cancel('chat:detail');
      };
    }

    async function loadDetail() {
      const ticket = requestCoordinatorRef.current.begin('chat:detail');
      setDetailState({ status: 'loading', item: null, error: null });
      try {
        const response = await getChatSession(activeSessionId, {
          signal: ticket.signal,
          correlationId: ticket.correlationId,
        });
        if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
        setDetailState({ status: 'success', item: mapChatSessionDetail(response), error: null });
      } catch (error) {
        if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
        setDetailState({ status: 'error', item: null, error: mapError(error) });
      } finally {
        requestCoordinatorRef.current.complete(ticket);
      }
    }

    loadDetail();
    return () => {
      requestCoordinatorRef.current.cancel('chat:detail');
    };
  }, [activeSessionId, isAuthReady, workspaceId]);

  async function handleCreateSession(event) {
    event.preventDefault();

    const title = titleInput.trim();
    if (!title) {
      return;
    }

    const ticket = requestCoordinatorRef.current.begin('chat:create-session');
    try {
      const created = mapChatSessionSummary(await createChatSession(
        { title },
        { signal: ticket.signal, correlationId: ticket.correlationId },
      ));
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setTitleInput('');
      setSessionsState((current) => ({
        status: 'success',
        items: [created, ...current.items.filter((item) => item.id !== created.id)],
        error: null,
      }));
      navigate(`/chat/${created.id}`);
    } catch (error) {
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setSessionsState((current) => ({ ...current, status: 'error', error: mapError(error) }));
    } finally {
      requestCoordinatorRef.current.complete(ticket);
    }
  }

  async function handleSubmitQuestion(event) {
    event.preventDefault();
    if (!activeSessionId || chatWriteInFlightRef.current) {
      return;
    }

    const question = questionInput.trim();
    if (!question) {
      return;
    }

    const ticket = requestCoordinatorRef.current.begin('chat:message');
    const ticketSessionId = activeSessionId;
    chatWriteInFlightRef.current = true;
    try {
      const response = mapPostedChatResponse(
        await postChatMessage(
          activeSessionId,
          { question, retrievalLimit: 8 },
          { signal: ticket.signal, correlationId: ticket.correlationId },
        ),
        { question },
      );
      if (!requestCoordinatorRef.current.isCurrent(ticket) || ticketSessionId !== activeSessionId) return;
      setQuestionInput('');
      setDetailState((current) => {
        const existingMessages = current.item?.messages || [];
        return {
          status: 'success',
          item: {
            ...(current.item || { id: activeSessionId, workspaceId, title: 'Chat', createdAtLabel: '', updatedAtLabel: '', messages: [] }),
            messages: [...existingMessages, response.userMessage, response.assistantMessage],
          },
          error: null,
        };
      });
      setSessionsState((current) => ({
        status: current.status === 'error' ? 'success' : current.status,
        items: current.items,
        error: null,
      }));
    } catch (error) {
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setDetailState((current) => ({ ...current, status: 'error', error: mapError(error) }));
    } finally {
      chatWriteInFlightRef.current = false;
      requestCoordinatorRef.current.complete(ticket);
    }
  }

  if (sessionsState.status === 'loading') {
    return <LoadingState label="Chat-Sessions werden geladen..." />;
  }

  if (sessionsState.status === 'error' && sessionsState.items.length === 0) {
    return <ErrorState error={sessionsState.error} />;
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="panel__eyebrow">M3c Chat</p>
          <h2>Dokumentgestuetzter Chat</h2>
        </div>
        <p className="page-header__meta">Workspace: {workspaceId || 'nicht konfiguriert'}</p>
      </div>

      <div className="chat-layout">
        <ChatSessionList items={sessionsState.items} activeSessionId={activeSessionId || null} />

        <section className="page-stack">
          <ChatComposer
            titleInput={titleInput}
            onTitleInputChange={setTitleInput}
            onCreateSession={handleCreateSession}
            questionInput={questionInput}
            onQuestionInputChange={setQuestionInput}
            onSubmitQuestion={handleSubmitQuestion}
            disabled={!activeSessionId}
          />

          {detailState.status === 'loading' ? <LoadingState label="Nachrichtenverlauf wird geladen..." /> : null}
          {detailState.status === 'error' ? <ErrorState error={detailState.error} /> : null}
          {detailState.status === 'idle' && sessionsState.items.length === 0 ? (
            <EmptyState
              title="Keine Chat-Sitzungen vorhanden"
              message="Lege zuerst eine neue Sitzung an, um dokumentgestuetzte Fragen zu stellen."
            />
          ) : null}
          {detailState.status === 'success' && detailState.item?.messages?.length === 0 ? (
            <EmptyState
              title="Noch keine Nachrichten vorhanden"
              message="Diese Sitzung ist angelegt, aber es wurde noch keine Frage gestellt."
            />
          ) : null}
          {detailState.status === 'success' && detailState.item?.messages?.length > 0 ? (
            <ChatMessageThread items={detailState.item.messages} />
          ) : null}
        </section>
      </div>
    </section>
  );
}
