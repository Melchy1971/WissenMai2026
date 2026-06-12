import React, { useState } from 'react';

function Section({ title, children }) {
  return React.createElement('section', { className: 'topic-detail-section' },
    React.createElement('h3', { className: 'topic-detail-section__title' }, title),
    children
  );
}

function ConfirmDialog({ action, onConfirm, onCancel, busy }) {
  return React.createElement('div', { className: 'confirm-overlay' },
    React.createElement('div', { className: 'confirm-dialog' },
      React.createElement('p', { className: 'confirm-dialog__msg' },
        'Thema "', action.name, '" wird dauerhaft gelöscht. Fortfahren?'
      ),
      React.createElement('div', { className: 'confirm-dialog__actions' },
        React.createElement('button', {
          className: 'button-secondary',
          onClick: onCancel,
          disabled: busy,
        }, 'Abbrechen'),
        React.createElement('button', {
          className: 'button-danger',
          onClick: onConfirm,
          disabled: busy,
        }, busy ? 'Wird gelöscht …' : 'Endgültig löschen')
      )
    )
  );
}

export function TopicDetailPanel({ detailState, selectedId, actionState, onDelete }) {
  var [confirm, setConfirm] = useState(null);

  var busy = actionState.status === 'loading';

  if (!selectedId) {
    return React.createElement('div', { className: 'topic-detail-panel panel topic-detail-panel--empty' },
      React.createElement('span', { className: 'topic-detail-panel__placeholder' }, 'Thema auswählen')
    );
  }

  if (detailState.status === 'loading') {
    return React.createElement('div', { className: 'topic-detail-panel panel topic-detail-panel--loading' },
      React.createElement('span', null, 'Thema wird geladen …')
    );
  }

  if (detailState.status === 'error') {
    var msg = (detailState.error && detailState.error.userMessage) || 'Fehler beim Laden.';
    return React.createElement('div', { className: 'topic-detail-panel panel topic-detail-panel--error' },
      React.createElement('strong', null, 'Fehler'),
      React.createElement('span', null, msg)
    );
  }

  var data = detailState.data;
  if (!data) return null;

  function handleDeleteClick() { setConfirm({ name: data.name }); }
  function handleConfirm() { onDelete(selectedId); setConfirm(null); }
  function handleCancel() { setConfirm(null); }

  return React.createElement('div', { className: 'topic-detail-panel panel' },
    confirm && React.createElement(ConfirmDialog, {
      action: confirm,
      onConfirm: handleConfirm,
      onCancel: handleCancel,
      busy: busy,
    }),

    React.createElement('div', { className: 'panel__header' },
      React.createElement('h2', { className: 'topic-detail-panel__title' }, data.name)
    ),

    React.createElement('div', { className: 'topic-detail-panel__body' },

      data.summary && React.createElement(Section, { title: 'Zusammenfassung' },
        React.createElement('p', { className: 'topic-detail__summary' }, data.summary)
      ),

      React.createElement(Section, { title: 'Dokumente' },
        data.documents.length === 0
          ? React.createElement('p', { className: 'topic-detail__none' }, 'Keine Dokumente zugeordnet.')
          : React.createElement('ul', { className: 'topic-detail-list' },
              data.documents.map(function(doc) {
                return React.createElement('li', { key: doc.id, className: 'topic-detail-list__item' },
                  React.createElement('span', { className: 'topic-detail-list__label' }, doc.title || doc.id),
                  React.createElement('span', { className: 'badge badge--neutral topic-detail-list__badge' }, doc.lifecycleStatus)
                );
              })
            )
      ),

      data.sources && data.sources.length > 0 && React.createElement(Section, { title: 'Quellen' },
        React.createElement('ul', { className: 'topic-detail-list' },
          data.sources.map(function(src, i) {
            return React.createElement('li', { key: src.docId + '-' + i, className: 'topic-detail-source' },
              React.createElement('span', { className: 'topic-detail-source__title' }, src.title),
              src.excerpt && React.createElement('blockquote', { className: 'topic-detail-source__excerpt' }, src.excerpt)
            );
          })
        )
      ),

      data.tags && data.tags.length > 0 && React.createElement(Section, { title: 'Tags' },
        React.createElement('div', { className: 'topic-detail-tags' },
          data.tags.map(function(tag) {
            return React.createElement('span', { key: tag, className: 'badge badge--neutral' }, tag);
          })
        )
      ),

      data.linkedTopics && data.linkedTopics.length > 0 && React.createElement(Section, { title: 'Verwandte Themen' },
        React.createElement('div', { className: 'topic-detail-linked' },
          data.linkedTopics.map(function(t) {
            return React.createElement('span', { key: t.id, className: 'badge' }, t.name);
          })
        )
      ),

      React.createElement(Section, { title: 'Aktionen' },
        actionState.status === 'error' && React.createElement('p', { className: 'topic-detail__action-error' },
          (actionState.error && actionState.error.userMessage) || 'Aktion fehlgeschlagen.'
        ),
        React.createElement('div', { className: 'topic-detail-actions' },
          React.createElement('button', {
            className: 'button-danger',
            onClick: handleDeleteClick,
            disabled: busy,
          }, 'Thema löschen')
        )
      )
    ),

    React.createElement('style', null, `
      .topic-detail-panel {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-width: 0;
        overflow: hidden;
      }
      .topic-detail-panel--empty,
      .topic-detail-panel--loading,
      .topic-detail-panel--error {
        justify-content: center;
        align-items: center;
        color: var(--color-text-secondary, #666);
        font-size: 14px;
        gap: 8px;
        flex-direction: column;
      }
      .topic-detail-panel__placeholder { color: var(--color-text-secondary, #666); font-size: 14px; }
      .topic-detail-panel__title { font-size: 18px; font-weight: 600; color: var(--color-text, #1c1c1c); margin: 0; }
      .topic-detail-panel__body { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 24px; }
      .topic-detail-section { display: flex; flex-direction: column; gap: 8px; }
      .topic-detail-section__title {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: var(--color-text-secondary, #666); margin: 0;
      }
      .topic-detail__summary { font-size: 14px; line-height: 1.6; color: var(--color-text, #1c1c1c); margin: 0; }
      .topic-detail__none { font-size: 13px; color: var(--color-text-secondary, #666); margin: 0; }
      .topic-detail-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
      .topic-detail-list__item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
      .topic-detail-list__label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .topic-detail-list__badge { flex-shrink: 0; }
      .topic-detail-source { display: flex; flex-direction: column; gap: 4px; }
      .topic-detail-source__title { font-size: 13px; font-weight: 500; }
      .topic-detail-source__excerpt {
        font-size: 12px; color: var(--color-text-secondary, #666);
        margin: 0; padding: 8px 12px;
        border-left: 3px solid var(--color-border, #ddd);
        font-style: italic; line-height: 1.5;
      }
      .topic-detail-tags, .topic-detail-linked { display: flex; flex-wrap: wrap; gap: 6px; }
      .topic-detail-actions { display: flex; gap: 8px; }
      .topic-detail__action-error { font-size: 12px; color: var(--color-danger, #880e4f); margin: 0 0 8px; }
      .button-danger {
        padding: 7px 16px; border-radius: 4px; font-size: 13px; font-weight: 500; cursor: pointer;
        border: 1px solid #c62828; background: #c62828; color: #fff;
      }
      .button-danger:disabled { opacity: 0.6; cursor: not-allowed; }
      .confirm-overlay {
        position: absolute; inset: 0; background: rgba(0,0,0,0.35);
        display: flex; align-items: center; justify-content: center; z-index: 50;
      }
      .confirm-dialog {
        background: var(--color-surface, #fff); border-radius: 8px;
        padding: 24px; max-width: 380px; width: 90%;
        box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        display: flex; flex-direction: column; gap: 20px;
      }
      .confirm-dialog__msg { margin: 0; font-size: 14px; line-height: 1.5; }
      .confirm-dialog__actions { display: flex; gap: 8px; justify-content: flex-end; }
    `)
  );
}
