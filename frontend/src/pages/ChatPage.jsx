import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { createChatSession, getChatSession, getChatSessions, postChatMessage } from '../api/chat.js';
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
  const { active_workspace_id: workspaceId, isAuthReady } = useAuth();

  const [sessionsState, setSessionsState] = useState({ status: 'loading', items: [], error: null });
  const [detailState, setDetailState] = useState({ status: 'idle', item: null, error: null });
  const [titleInput, setTitleInput] = useState('');
  const [questionInput, setQuestionInput] = useState('');

  useEffect(() => {
    let cancelled = false;

    if (!isAuthReady) {
      setSessionsState({ status: 'loading', items: [], error: null });
      return () => {
        cancelled = true;
      };
    }

    async function loadSessions() {
      setSessionsState({ status: 'loading', items: [], error: null });
      try {
        const response = await getChatSessions({ limit: 20, offset: 0 });
        if (cancelled) return;
        const items = response.map(mapChatSessionSummary);
        setSessionsState({ status: 'success', items, error: null });
        if (!activeSessionId && items.length > 0) {
          navigate(`/chat/${items[0].id}`, { replace: true });
        }
      } catch (error) {
        if (cancelled) return;
        setSessionsState({ status: 'error', items: [], error: mapError(error) });
      }
    }

    loadSessions();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, navigate, workspaceId, isAuthReady]);

  useEffect(() => {
    let cancelled = false;
    if (!isAuthReady) {
      setDetailState({ status: 'loading', item: null, error: null });
      return () => {
        cancelled = true;
      };
    }
    if (!activeSessionId) {
      setDetailState({ status: 'idle', item: null, error: null });
      return () => {
        cancelled = true;
      };
    }

    async function loadDetail() {
      setDetailState({ status: 'loading', item: null, error: null });
      try {
        const response = await getChatSession(activeSessionId);
        if (cancelled) return;
        setDetailState({ status: 'success', item: mapChatSessionDetail(response), error: null });
      } catch (error) {
        if (cancelled) return;
        setDetailState({ status: 'error', item: null, error: mapError(error) });
      }
    }

    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, isAuthReady]);

  async function handleCreateSession(event) {
    event.preventDefault();

    const title = titleInput.trim();
    if (!title) {
      return;
    }

    try {
      const created = mapChatSessionSummary(await createChatSession({ title }));
      setTitleInput('');
      setSessionsState((current) => ({
        status: 'success',
        items: [created, ...current.items.filter((item) => item.id !== created.id)],
        error: null,
      }));
      navigate(`/chat/${created.id}`);
    } catch (error) {
      setSessionsState((current) => ({ ...current, status: 'error', error: mapError(error) }));
    }
  }

  async function handleSubmitQuestion(event) {
    event.preventDefault();
    if (!activeSessionId) {
      return;
    }

    const question = questionInput.trim();
    if (!question) {
      return;
    }

    try {
      const response = mapPostedChatResponse(
        await postChatMessage(activeSessionId, { question, retrievalLimit: 8 }),
        { question },
      );
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
      setDetailState((current) => ({ ...current, status: 'error', error: mapError(error) }));
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
