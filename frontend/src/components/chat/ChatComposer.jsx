export function ChatComposer({
  titleInput,
  onTitleInputChange,
  onCreateSession,
  questionInput,
  onQuestionInputChange,
  onSubmitQuestion,
  disabled,
}) {
  return (
    <section className="panel chat-composer-panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Neuer Chat</p>
          <h3>Sitzung und Frage</h3>
        </div>
      </div>

      <form className="chat-composer" onSubmit={onCreateSession}>
        <label className="search-bar__field">
          <span className="search-bar__label">Titel der Sitzung</span>
          <input
            data-testid="chat-session-title"
            type="text"
            value={titleInput}
            onChange={(event) => onTitleInputChange(event.target.value)}
            placeholder="z. B. Vertragsanalyse Mai"
          />
        </label>
        <div className="search-bar__actions">
          <button data-testid="chat-new-session" type="submit">Neue Sitzung</button>
        </div>
      </form>

      <form className="chat-composer" onSubmit={onSubmitQuestion}>
        <label className="search-bar__field">
          <span className="search-bar__label">Frage</span>
          <textarea
            data-testid="chat-input"
            value={questionInput}
            onChange={(event) => onQuestionInputChange(event.target.value)}
            placeholder="Frage an den Dokumentbestand stellen"
            rows={4}
            disabled={disabled}
          />
        </label>
        <div className="search-bar__actions">
          <button data-testid="chat-submit" type="submit" disabled={disabled}>Frage senden</button>
        </div>
      </form>
    </section>
  );
}
