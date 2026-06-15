export function ChatMessageThread({ items }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Verlauf</p>
          <h3>Nachrichten</h3>
        </div>
      </div>
      <ul className="stack-list" data-testid="chat-message-list">
        {items.map((item) => (
          <li
            key={item.id}
            className={`stack-list__item stack-list__item--block chat-message chat-message--${item.role}`}
            data-testid={item.role === 'assistant' ? 'chat-answer' : undefined}
          >
            <div className="chat-message__header">
              <strong>{item.role === 'user' ? 'Frage' : 'Antwort'}</strong>
              <span className="state-card__meta">{item.createdAtLabel}</span>
            </div>
            {item.role === 'assistant' && item.usedRagContext && item.sources.length === 0 ? (
              <div className="chat-warning" data-testid="rag-answer-blocked">
                <strong>Antwort blockiert</strong>
                <p>Fuer diese RAG-Antwort sind keine sichtbaren Quellen verfuegbar.</p>
                {item.blockedSourceCount > 0 ? (
                  <p className="state-card__meta">Gesperrte Quellen: {item.blockedSourceCount}</p>
                ) : null}
              </div>
            ) : (
              <p className="chat-message__content">{item.content}</p>
            )}
            {item.confidence && item.confidence.sufficientContext === false ? (
              <div className="chat-warning" data-testid="chat-insufficient-context">
                <strong>Zu wenig Kontext</strong>
                <p>Die Antwort wurde als unzureichend belegt markiert.</p>
                <p className="state-card__meta">Max Score: {item.confidence.retrievalScoreMaxLabel} · Avg Score: {item.confidence.retrievalScoreAvgLabel}</p>
              </div>
            ) : null}
            {Array.isArray(item.citations) && item.citations.length > 0 ? (
              <div className="chat-citations" data-testid={item.usedRagContext ? 'source-list' : 'chat-citations'}>
                <p className="panel__eyebrow">Quellen</p>
                <ul className="stack-list">
                  {item.citations.map((citation) => (
                    <li key={`${item.id}-${citation.chunkId}`} className="stack-list__item stack-list__item--block chat-citation-card">
                      <p><strong>{citation.documentTitle}</strong></p>
                      <p className="state-card__meta">Chunk: {citation.chunkId} · {citation.sourceAnchorLabel}</p>
                      <p className="state-card__meta">Source Status: {citation.sourceStatus}</p>
                      <p>{citation.quotePreview}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {item.usedRagContext && item.sources.length > 0 && (!Array.isArray(item.citations) || item.citations.length === 0) ? (
              <div className="chat-citations" data-testid="source-list">
                <p className="panel__eyebrow">Quellen</p>
                <ul className="stack-list">
                  {item.sources.map((source) => (
                    <li key={`${item.id}-${source.chunkId || source.documentName}`} className="stack-list__item stack-list__item--block chat-citation-card">
                      <p><strong>{source.documentName}</strong></p>
                      <p className="state-card__meta">
                        Chunk: {source.chunkId || 'unbekannt'}
                        {source.page != null ? ` · Seite ${source.page}` : ''}
                        {source.score != null ? ` · Score ${source.score.toFixed(3)}` : ''}
                        {` · ${source.classification}`}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
