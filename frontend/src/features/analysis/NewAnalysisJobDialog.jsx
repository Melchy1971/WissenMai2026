import React, { useState, useCallback, useEffect } from 'react';
import { analysisApi } from '../../api/analysis.js';

// ─── Constants ──────────────────────────────────────────────────────────────

var ANALYSIS_TYPES = [
  { value: 'SUMMARIZE',  label: 'Zusammenfassung',   desc: 'Dokumente zusammenfassen und Kernaussagen extrahieren' },
  { value: 'COMPARE',    label: 'Vergleich',          desc: 'Überschneidungen und Unterschiede zwischen Dokumenten' },
  { value: 'CLASSIFY',   label: 'Klassifikation',     desc: 'Themen, Tags und Kategorien vorschlagen' },
  { value: 'EXTRACT',    label: 'Extraktion',         desc: 'Strukturierte Daten und Fakten aus Texten gewinnen' },
  { value: 'CUSTOM',     label: 'Benutzerdefiniert',  desc: 'Eigenen Prompt formulieren' },
];

var SOURCE_TYPES = [
  { value: 'DOCUMENTS',     label: 'Dokumente',       desc: 'Einzelne Dokumente aus der Wissensbasis' },
  { value: 'TOPIC',         label: 'Thema',           desc: 'Alle Dokumente eines Themas' },
  { value: 'SEARCH_RESULT', label: 'Suchergebnis',    desc: 'Ergebnisse einer vorherigen Suche' },
];

var PROVIDERS = [
  { value: 'ollama',  label: 'Ollama (lokal)',       models: ['llama3', 'llama3.1', 'mistral', 'codellama'] },
  { value: 'openai',  label: 'OpenAI',               models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
  { value: 'gemini',  label: 'Google Gemini',        models: ['gemini-1.5-flash', 'gemini-1.5-pro'] },
];

var DEFAULT_PROMPTS = {
  SUMMARIZE:  'Fasse die wichtigsten Inhalte der ausgewählten Dokumente zusammen. Extrahiere die Kernaussagen als strukturierte Liste.',
  COMPARE:    'Vergleiche die ausgewählten Dokumente. Zeige Überschneidungen, Widersprüche und Ergänzungsmöglichkeiten auf.',
  CLASSIFY:   'Analysiere die Dokumente und schlage geeignete Tags, Themen und Kategorien für die Wissensbasis vor.',
  EXTRACT:    'Extrahiere strukturierte Informationen aus den Dokumenten: Fakten, Entitäten, Zahlen und Schlüsselbegriffe.',
  CUSTOM:     '',
};

var TOTAL_STEPS = 5;

// ─── Styles ──────────────────────────────────────────────────────────────────

var OVERLAY_STYLE = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.5)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 1000,
};

var DIALOG_STYLE = {
  background: 'var(--color-surface)',
  borderRadius: 'var(--radius-xl)',
  boxShadow: 'var(--shadow-xl)',
  width: '620px',
  maxWidth: '95vw',
  maxHeight: '85vh',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

var DIALOG_HEADER_STYLE = {
  padding: '20px 24px 16px',
  borderBottom: '1px solid var(--color-border)',
  flexShrink: 0,
};

var PROGRESS_TRACK_STYLE = {
  display: 'flex',
  gap: '6px',
  marginTop: '12px',
};

var DIALOG_BODY_STYLE = {
  flex: 1,
  overflowY: 'auto',
  padding: '20px 24px',
};

var DIALOG_FOOTER_STYLE = {
  padding: '14px 24px',
  borderTop: '1px solid var(--color-border)',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexShrink: 0,
  gap: '8px',
};

var BTN_PRIMARY = {
  border: 'none', borderRadius: 'var(--radius-md)',
  padding: '8px 18px', fontSize: '13px', fontWeight: 600,
  cursor: 'pointer', background: 'var(--t-magenta)', color: '#fff',
};

var BTN_SECONDARY = {
  border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)',
  padding: '8px 16px', fontSize: '13px', fontWeight: 500,
  cursor: 'pointer', background: 'transparent', color: 'var(--color-text)',
};

var BTN_GHOST = {
  border: 'none', borderRadius: 'var(--radius-md)',
  padding: '8px 12px', fontSize: '13px',
  cursor: 'pointer', background: 'transparent', color: 'var(--color-text-secondary)',
};

var CARD_STYLE = {
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: '12px 14px',
  cursor: 'pointer',
  marginBottom: '8px',
  display: 'flex',
  alignItems: 'flex-start',
  gap: '10px',
};

var CARD_SELECTED_STYLE = Object.assign({}, CARD_STYLE, {
  border: '2px solid var(--t-magenta)',
  background: 'var(--t-magenta-10)',
});

var LABEL_STYLE = {
  fontSize: '11px', fontWeight: 600,
  color: 'var(--color-text-tertiary)',
  textTransform: 'uppercase', letterSpacing: '0.05em',
  marginBottom: '6px', display: 'block',
};

var INPUT_STYLE = {
  width: '100%', boxSizing: 'border-box',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: '8px 10px', fontSize: '13px',
  background: 'var(--color-bg)',
  color: 'var(--color-text)',
};

var TEXTAREA_STYLE = Object.assign({}, INPUT_STYLE, {
  resize: 'vertical', minHeight: '100px', fontFamily: 'inherit', lineHeight: '1.5',
});

var ERROR_STYLE = {
  color: 'var(--color-danger-fg)',
  background: 'var(--color-danger-bg)',
  borderRadius: 'var(--radius-md)',
  padding: '8px 12px',
  fontSize: '12px',
  marginTop: '12px',
};

// ─── Step Components ──────────────────────────────────────────────────────────

function StepAnalysisType({ form, setForm }) {
  return (
    <div>
      <p style={{ margin: '0 0 14px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        Welche Art von Analyse soll durchgeführt werden?
      </p>
      {ANALYSIS_TYPES.map(function(t) {
        var selected = form.analysisType === t.value;
        return (
          <div
            key={t.value}
            style={selected ? CARD_SELECTED_STYLE : CARD_STYLE}
            onClick={function() { setForm(function(f) { return Object.assign({}, f, { analysisType: t.value, prompt: DEFAULT_PROMPTS[t.value] }); }); }}
            data-testid={'type-' + t.value.toLowerCase()}
            role="radio"
            aria-checked={selected}
          >
            <div style={{ marginTop: '1px', color: selected ? 'var(--t-magenta)' : 'var(--color-text-tertiary)' }}>
              {selected ? '◉' : '○'}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-text)' }}>{t.label}</div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>{t.desc}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StepSourceType({ form, setForm }) {
  return (
    <div>
      <p style={{ margin: '0 0 14px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        Welche Datenquelle soll analysiert werden?
      </p>
      {SOURCE_TYPES.map(function(s) {
        var selected = form.sourceType === s.value;
        return (
          <div
            key={s.value}
            style={selected ? CARD_SELECTED_STYLE : CARD_STYLE}
            onClick={function() { setForm(function(f) { return Object.assign({}, f, { sourceType: s.value, sourceDocumentIds: [] }); }); }}
            data-testid={'source-' + s.value.toLowerCase()}
            role="radio"
            aria-checked={selected}
          >
            <div style={{ marginTop: '1px', color: selected ? 'var(--t-magenta)' : 'var(--color-text-tertiary)' }}>
              {selected ? '◉' : '○'}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-text)' }}>{s.label}</div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>{s.desc}</div>
            </div>
          </div>
        );
      })}

      {form.sourceType === 'DOCUMENTS' && (
        <div style={{ marginTop: '16px' }}>
          <label style={LABEL_STYLE}>Dokument-IDs (eine pro Zeile)</label>
          <textarea
            style={TEXTAREA_STYLE}
            data-testid="input-doc-ids"
            placeholder="doc-uuid-1&#10;doc-uuid-2"
            value={form.sourceDocumentIds.join('\n')}
            onChange={function(e) {
              var ids = e.target.value.split('\n').map(function(s) { return s.trim(); }).filter(Boolean);
              setForm(function(f) { return Object.assign({}, f, { sourceDocumentIds: ids }); });
            }}
          />
          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '4px' }}>
            {form.sourceDocumentIds.length} Dokument(e) ausgewählt
          </div>
        </div>
      )}
    </div>
  );
}

function StepPrompt({ form, setForm }) {
  var isCustom = form.analysisType === 'CUSTOM';
  return (
    <div>
      <p style={{ margin: '0 0 14px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        {isCustom
          ? 'Formuliere einen eigenen Analyse-Prompt.'
          : 'Der Standardprompt kann angepasst werden.'}
      </p>
      <label style={LABEL_STYLE}>Analyse-Prompt</label>
      <textarea
        style={Object.assign({}, TEXTAREA_STYLE, { minHeight: '140px' })}
        data-testid="input-prompt"
        value={form.prompt}
        onChange={function(e) { setForm(function(f) { return Object.assign({}, f, { prompt: e.target.value }); }); }}
        placeholder="Was soll die KI analysieren?"
      />
      <div style={{ fontSize: '11px', color: form.prompt.length > 4000 ? 'var(--color-danger-fg)' : 'var(--color-text-tertiary)', marginTop: '4px', textAlign: 'right' }}>
        {form.prompt.length} / 4000 Zeichen
      </div>
    </div>
  );
}

function StepProvider({ form, setForm }) {
  var selectedProvider = PROVIDERS.find(function(p) { return p.value === form.provider; });

  return (
    <div>
      <p style={{ margin: '0 0 14px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        Welcher KI-Provider und welches Modell soll genutzt werden?
      </p>

      <label style={LABEL_STYLE}>Provider</label>
      {PROVIDERS.map(function(p) {
        var selected = form.provider === p.value;
        return (
          <div
            key={p.value}
            style={selected ? CARD_SELECTED_STYLE : CARD_STYLE}
            onClick={function() { setForm(function(f) { return Object.assign({}, f, { provider: p.value, model: p.models[0] }); }); }}
            data-testid={'provider-' + p.value}
            role="radio"
            aria-checked={selected}
          >
            <div style={{ marginTop: '1px', color: selected ? 'var(--t-magenta)' : 'var(--color-text-tertiary)' }}>
              {selected ? '◉' : '○'}
            </div>
            <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-text)' }}>{p.label}</div>
          </div>
        );
      })}

      {selectedProvider && (
        <div style={{ marginTop: '16px' }}>
          <label style={LABEL_STYLE}>Modell</label>
          <select
            style={INPUT_STYLE}
            data-testid="select-model"
            value={form.model}
            onChange={function(e) { setForm(function(f) { return Object.assign({}, f, { model: e.target.value }); }); }}
          >
            {selectedProvider.models.map(function(m) {
              return <option key={m} value={m}>{m}</option>;
            })}
          </select>
          <input
            style={Object.assign({}, INPUT_STYLE, { marginTop: '8px' })}
            data-testid="input-model-custom"
            placeholder="Oder eigenes Modell eingeben…"
            value={selectedProvider.models.includes(form.model) ? '' : form.model}
            onChange={function(e) {
              if (e.target.value) setForm(function(f) { return Object.assign({}, f, { model: e.target.value }); });
            }}
          />
        </div>
      )}
    </div>
  );
}

function StepConfirm({ form }) {
  var typeMeta = ANALYSIS_TYPES.find(function(t) { return t.value === form.analysisType; });
  var sourceMeta = SOURCE_TYPES.find(function(s) { return s.value === form.sourceType; });
  var providerMeta = PROVIDERS.find(function(p) { return p.value === form.provider; });

  function Row({ label, value }) {
    return (
      <div style={{ display: 'flex', gap: '12px', padding: '8px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
        <span style={{ width: '120px', flexShrink: 0, fontSize: '11px', fontWeight: 600, color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', paddingTop: '1px' }}>
          {label}
        </span>
        <span style={{ fontSize: '13px', color: 'var(--color-text)', flex: 1, wordBreak: 'break-word' }}>{value}</span>
      </div>
    );
  }

  return (
    <div>
      <p style={{ margin: '0 0 14px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        Überprüfe die Konfiguration vor dem Start.
      </p>
      <div style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '0 14px' }}>
        <Row label="Analyse-Typ" value={typeMeta ? typeMeta.label : form.analysisType} />
        <Row label="Quelle" value={sourceMeta ? sourceMeta.label : form.sourceType || '—'} />
        {form.sourceDocumentIds.length > 0 && (
          <Row label="Dokumente" value={form.sourceDocumentIds.length + ' ausgewählt'} />
        )}
        <Row label="Provider" value={(providerMeta ? providerMeta.label : form.provider) + (form.model ? ' / ' + form.model : '')} />
        <Row label="Prompt" value={form.prompt.length > 120 ? form.prompt.slice(0, 120) + '…' : form.prompt} />
      </div>
    </div>
  );
}

// ─── Progress dots ────────────────────────────────────────────────────────────

function ProgressDots({ step }) {
  return (
    <div style={PROGRESS_TRACK_STYLE} aria-label={'Schritt ' + step + ' von ' + TOTAL_STEPS}>
      {Array.from({ length: TOTAL_STEPS }).map(function(_, i) {
        var done   = i + 1 < step;
        var active = i + 1 === step;
        return (
          <div
            key={i}
            style={{
              flex: 1, height: '4px', borderRadius: '2px',
              background: done || active ? 'var(--t-magenta)' : 'var(--color-border)',
              opacity: done ? 0.5 : 1,
              transition: 'background 0.2s',
            }}
          />
        );
      })}
    </div>
  );
}

// ─── Validation ───────────────────────────────────────────────────────────────

function validateStep(step, form) {
  if (step === 1 && !form.analysisType) return 'Bitte einen Analyse-Typ wählen.';
  if (step === 2 && !form.sourceType)   return 'Bitte eine Datenquelle wählen.';
  if (step === 2 && form.sourceType === 'DOCUMENTS' && form.sourceDocumentIds.length === 0)
    return 'Mindestens ein Dokument muss angegeben werden.';
  if (step === 3 && !form.prompt.trim()) return 'Prompt darf nicht leer sein.';
  if (step === 3 && form.prompt.length > 4000) return 'Prompt darf max. 4000 Zeichen lang sein.';
  if (step === 4 && !form.provider)     return 'Bitte einen Provider wählen.';
  if (step === 4 && !form.model)        return 'Bitte ein Modell wählen.';
  return null;
}

var STEP_TITLES = ['Analyse-Typ', 'Datenquelle', 'Prompt', 'KI-Provider', 'Bestätigen'];

// ─── Main Dialog ──────────────────────────────────────────────────────────────

var INITIAL_FORM = {
  analysisType: '',
  sourceType: '',
  sourceDocumentIds: [],
  prompt: '',
  provider: 'ollama',
  model: 'llama3',
};

export function NewAnalysisJobDialog({ open, onClose, onJobCreated }) {
  var [step, setStep]       = useState(1);
  var [form, setForm]       = useState(INITIAL_FORM);
  var [stepError, setStepError] = useState(null);
  var [submitError, setSubmitError] = useState(null);
  var [submitting, setSubmitting]   = useState(false);

  // Reset on open
  useEffect(function() {
    if (open) {
      setStep(1);
      setForm(INITIAL_FORM);
      setStepError(null);
      setSubmitError(null);
      setSubmitting(false);
    }
  }, [open]);

  // Close on Escape
  useEffect(function() {
    if (!open) return;
    function handler(e) { if (e.key === 'Escape' && !submitting) onClose(); }
    window.addEventListener('keydown', handler);
    return function() { window.removeEventListener('keydown', handler); };
  }, [open, submitting, onClose]);

  var handleNext = useCallback(function() {
    var err = validateStep(step, form);
    if (err) { setStepError(err); return; }
    setStepError(null);
    setStep(function(s) { return s + 1; });
  }, [step, form]);

  var handleBack = useCallback(function() {
    setStepError(null);
    setStep(function(s) { return s - 1; });
  }, []);

  var handleSubmit = useCallback(function() {
    setSubmitError(null);
    setSubmitting(true);
    analysisApi.createAnalysisJob({
      analysis_type:       form.analysisType,
      source_type:         form.sourceType || null,
      source_document_ids: form.sourceDocumentIds,
      prompt:              form.prompt,
      provider:            form.provider,
      model:               form.model,
    }).then(function(job) {
      setSubmitting(false);
      onJobCreated(job);
      onClose();
    }).catch(function(err) {
      setSubmitting(false);
      setSubmitError((err && err.userMessage) || 'Analyse konnte nicht gestartet werden.');
    });
  }, [form, onJobCreated, onClose]);

  if (!open) return null;

  return (
    <div style={OVERLAY_STYLE} onClick={function(e) { if (e.target === e.currentTarget && !submitting) onClose(); }}
      data-testid="new-analysis-dialog">
      <div style={DIALOG_STYLE} role="dialog" aria-modal="true" aria-label="Neue Analyse erstellen">

        {/* Header */}
        <div style={DIALOG_HEADER_STYLE}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text)' }}>
                Neue Analyse
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                Schritt {step} von {TOTAL_STEPS} — {STEP_TITLES[step - 1]}
              </div>
            </div>
            <button style={BTN_GHOST} onClick={onClose} disabled={submitting} aria-label="Schließen">✕</button>
          </div>
          <ProgressDots step={step} />
        </div>

        {/* Body */}
        <div style={DIALOG_BODY_STYLE}>
          {step === 1 && <StepAnalysisType form={form} setForm={setForm} />}
          {step === 2 && <StepSourceType   form={form} setForm={setForm} />}
          {step === 3 && <StepPrompt       form={form} setForm={setForm} />}
          {step === 4 && <StepProvider     form={form} setForm={setForm} />}
          {step === 5 && <StepConfirm      form={form} />}

          {stepError && (
            <div style={ERROR_STYLE} data-testid="step-error">{stepError}</div>
          )}
          {submitError && (
            <div style={ERROR_STYLE} data-testid="submit-error">{submitError}</div>
          )}
        </div>

        {/* Footer */}
        <div style={DIALOG_FOOTER_STYLE}>
          <button style={BTN_SECONDARY} onClick={step === 1 ? onClose : handleBack} disabled={submitting}
            data-testid="btn-back">
            {step === 1 ? 'Abbrechen' : '← Zurück'}
          </button>

          {step < TOTAL_STEPS ? (
            <button style={BTN_PRIMARY} onClick={handleNext} data-testid="btn-next">
              Weiter →
            </button>
          ) : (
            <button
              style={Object.assign({}, BTN_PRIMARY, { opacity: submitting ? 0.6 : 1 })}
              onClick={handleSubmit}
              disabled={submitting}
              data-testid="btn-submit"
            >
              {submitting ? 'Wird gestartet…' : 'Analyse starten'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
