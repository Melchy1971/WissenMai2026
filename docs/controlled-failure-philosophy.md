# Controlled Failure Philosophy

Stand: 2026-05-13

## Ziel

Fehler sind kein Ausnahmezustand — sie sind erwartet und müssen sichtbar, deterministisch und reparierbar sein. Ein System, das Fehler verbirgt, erzeugt stille Degeneration. Ein System, das Fehler explizit macht, bleibt kontrollierbar.

Verwandte Dokumente:

- `docs/operational-truth-governance.md` — Gate-Policies und Truth-Quellen
- `docs/operational-sla-framework.md` — SLA-Schwellen und Eskalationsregeln
- `docs/architecture-change-governance.md` — Change-Control und Rollback
- `backend/app/core/errors.py` — kanonische Fehlercodes

---

## 1. Fehlerprinzipien

### Prinzip 1: Keine stillen Fehler

Jeder Fehler erzeugt ein sichtbares, strukturiertes Ereignis. Ein Fehler, der keinen Log-Eintrag, keinen Fehlerstatus und keinen Retry-Marker hinterlässt, existiert für das System nicht — aber sein Schaden akkumuliert.

Regeln:

- Jede Exception wird entweder als HTTP-Fehlerantwort (API-Grenze) oder als strukturiertes Log-Event (Hintergrundpfad) sichtbar gemacht.
- Catch-All-Handler ohne strukturiertes Logging sind verboten.
- Jeder Background-Job-Fehler setzt den Job-Status auf `failed` oder `retryable` mit Fehlerklasse und Zähler.
- Ein Job, der still endet ohne Status-Update, ist ein Governance-Verstoß.

```json
{
  "event_name": "job_failed",
  "job_id": "...",
  "job_type": "document_import",
  "workspace_id": "...",
  "error_code": "IMPORT_FAILED",
  "error_class": "ImportFailedApiError",
  "attempt": 2,
  "max_attempts": 3,
  "status_transition": "running → retryable"
}
```

### Prinzip 2: Keine stillen Retries

Jeder Retry ist sichtbar, gezählt und begrenzt.

Regeln:

- Retry-Versuche werden in `background_jobs.attempts` gezählt und in strukturierten Log-Events protokolliert.
- Maximale Retry-Anzahl ist pro Job-Typ konfiguriert und wird nicht dynamisch überschritten.
- Ein Job, der die maximale Retry-Anzahl erreicht, wechselt deterministisch in `dead_letter` — nicht in `pending` zurück.
- Kein Retry ohne expliziten `retry_after`-Zeitstempel oder exponentielles Backoff mit dokumentiertem Faktor.
- Retry-Schleifen ohne Abbruchbedingung sind verboten.

Metrik: `m5_retry_frequency` (Retries/Stunde je Workspace und Job-Typ); `m5_dead_letter_growth` (Dead-Letter-Wachstum je 24h).

### Prinzip 3: Keine impliziten Datenkorrekturen

Daten werden nicht still repariert. Eine automatische Korrektur ohne Audit-Spur ist eine verdeckte Mutation.

Regeln:

- Orphan-Chunks, veraltete Indizes und inkonsistente Lifecycle-Zustände werden erkannt und gemeldet, nicht still bereinigt.
- Repair-Operationen sind explizite, auditierte Aktionen mit Dry-Run-Pflicht vor jeder Mutation.
- Backfill-Migrationen erzeugen Audit-Log-Einträge (`migration_document_repairs` oder Äquivalent).
- Kein ORM-Hook oder Trigger darf Daten silent korrigieren, ohne einen Log-Eintrag zu erzeugen.
- Cleanup-Governance-Service schreibt vor jeder destructiven Aktion einen Dry-Run-Report; `blocked_count = 0` ist Gate-Bedingung.

### Prinzip 4: Kein „Best Effort" ohne Audit

Wenn eine Operation partiell gelingt, ist der partielle Erfolg explizit dokumentiert — nicht als Gesamterfolg gemeldet.

Regeln:

- HTTP 200 darf nur zurückgegeben werden, wenn die Operation vollständig und konsistent abgeschlossen ist.
- Partielle Ergebnisse erhalten HTTP 207 (Multi-Status) mit expliziter Erfolgs/Fehler-Liste.
- Admin-Aktionen mit Dry-Run-Modus melden Dry-Run-Ergebnis als eigenen Status, nicht als Erfolg.
- Retrieval gibt `INSUFFICIENT_CONTEXT` zurück, wenn keine ausreichende Grundlage existiert — kein Halluzinations-Fallback, kein implizites „beste Antwort trotzdem".
- Batch-Operationen (z.B. Reindex mehrerer Dokumente) melden Erfolg und Fehler je Dokument, nicht einen aggregierten „fertig"-Status.

### Prinzip 5: Keine verdeckten Fallbacks

Wenn ein primärer Pfad fehlschlägt, ist der Fallback explizit, sichtbar und kein transparenter Ersatz.

Regeln:

- LLM-Unavailability erzeugt `LLM_UNAVAILABLE` (HTTP 503) — kein Fallback auf gecachte oder synthetische Antworten ohne Client-Wissen.
- Search-Fallback (z.B. reduziertes Retrieval-Fenster) ist als `degraded` gekennzeichnet, nicht als normaler Retrieval-Erfolg.
- Backup-Verify-Fehler führt nicht zu „Backup trotzdem als gültig markieren" — der Fehler bleibt sichtbar bis zu einem erfolgreichen Re-Verify.
- Ein Advisory-Lock-Timeout erzeugt `RESOURCE_LOCKED` (HTTP 409) — keine transparente Wartezeit ohne Client-Signal.

---

## 2. Standardisierte Fehlercodes

Alle API-Fehler folgen dem Schema in `backend/app/core/errors.py`. Jede Fehlerklasse hat einen fixen HTTP-Statuscode und einen maschinenlesbaren `code`.

### 2.1 Fehlercode-Kategorien

| HTTP | Kategorie | Codes (Auswahl) |
|---|---|---|
| 401 | Auth | `AUTH_REQUIRED`, `UNAUTHORIZED`, `AUTH_INVALID_CREDENTIALS` |
| 403 | Zugriff | `WORKSPACE_ACCESS_FORBIDDEN`, `ADMIN_REQUIRED`, `FORBIDDEN` |
| 404 | Nicht gefunden | `DOCUMENT_NOT_FOUND`, `CHAT_SESSION_NOT_FOUND`, `JOB_NOT_FOUND` |
| 409 | Zustandskonflikt | `DOCUMENT_STATE_CONFLICT`, `INVALID_LIFECYCLE_TRANSITION`, `RESOURCE_LOCKED`, `JOB_NOT_REPLAYABLE`, `DUPLICATE_DOCUMENT`, `DOCUMENT_ALREADY_ARCHIVED`, `DOCUMENT_ALREADY_DELETED` |
| 413 | Kapazität | `FILE_TOO_LARGE` |
| 415 | Format | `UNSUPPORTED_FILE_TYPE` |
| 422 | Semantik | `INVALID_QUERY`, `INVALID_PAGINATION`, `CHAT_MESSAGE_INVALID`, `INSUFFICIENT_CONTEXT`, `OCR_REQUIRED`, `PARSER_FAILED`, `INVALID_LIFECYCLE_STATUS`, `REINDEX_CONSTRAINT_VIOLATION`, `BACKUP_VALIDATION_FAILED` |
| 500 | Systemfehler | `INTERNAL_ERROR`, `IMPORT_FAILED`, `CHAT_PERSISTENCE_FAILED`, `DIAGNOSTICS_FAILED`, `REPLAY_FAILED` |
| 501 | Nicht implementiert | `ADMIN_ACTION_NOT_IMPLEMENTED` |
| 502 | Upstream | `RETRIEVAL_FAILED` |
| 503 | Nicht verfügbar | `LLM_UNAVAILABLE`, `SERVICE_UNAVAILABLE` |

### 2.2 Regeln für neue Fehlercodes

- Jeder neue Fehlercode ist eine Unterklasse von `ApiError` in `backend/app/core/errors.py`.
- HTTP-Statuscode und `code`-String sind in der Klasse fest; kein dynamisches Setzen per Instanz.
- Keine zwei Fehlerklassen dürfen denselben `code`-String haben.
- Neue Fehlercodes für neue Domänen (z.B. neuer Queue-Job-Typ oder neuer Admin-Bereich) brauchen einen postgres_truth-Test, der den Fehlercode im entsprechenden Fehlerpfad verifiziert.
- Fehlercodes werden nie umbenannt — das ist ein Breaking API Change.

### 2.3 Fehlerantwort-Format

```json
{
  "error": {
    "code": "IMPORT_FAILED",
    "message": "Document import failed",
    "details": {
      "document_id": "...",
      "stage": "chunking",
      "attempt": 2
    }
  }
}
```

`details` ist optional aber strukturiert — kein freier Textblock, keine Stack-Traces in Produktion.

---

## 3. Recovery explizit machen

Recovery ist kein automatischer Hintergrundprozess — sie ist eine explizite, dokumentierte Aktion mit definiertem Eintrittspunkt, Ausgangszustand und Verifikation.

### 3.1 Recovery-Kategorien

| Kategorie | Eintrittspunkt | Verifikation |
|---|---|---|
| Job-Retry | automatisch via Retry-Policy | `background_jobs.attempts` + Log-Event |
| Job-Replay | explizit via Admin-API `POST /admin/jobs/{id}/replay` | Job-Status nach Replay + Truth-Test |
| Advisory-Lock-Recovery | automatisch nach Lock-Timeout; kein stillerRetry | `RESOURCE_LOCKED` + neuer Versuch durch Aufrufer |
| Reindex-Recovery | explizit via `ReindexGovernanceService` | `test_reindex_governance_truth.py` grün | Quelle: `reports/current/masterplan_status.json`.
| Cleanup-Recovery | explizit via Dry-Run → Mutation mit Gate | Cleanup-Dry-Run-Report + `blocked_count = 0` |
| Restore-Recovery | explizit via `BackupRestoreService` + Verify | Restore-Truth-Report + postgres_truth-Smoke |
| Drift-Repair | explizit via Runbook | Drift-Report nach Repair + `m5_drift_score = 0` |

### 3.2 Recovery-Invarianten

- Jede Recovery-Aktion startet mit einer Zustandsprüfung, nicht blind.
- Kein Recovery-Pfad mutiert Daten ohne vorherige Dry-Run- oder Read-Phase.
- Recovery-Aktionen werden als Admin-Audit-Event protokolliert.
- Nach abgeschlossener Recovery: Verifikation über Truth-Test oder Report — kein „looks good"-Status.
- Ein fehlgeschlagener Recovery-Versuch wechselt in `blocked`, nicht zurück in `pending`.

### 3.3 Recovery-Verbote

- Kein Recovery durch stille Datenlöschung inkonsistenter Einträge ohne Audit.
- Kein Recovery durch `DELETE FROM background_jobs WHERE status = 'dead_letter'` ohne Replay-Prüfung.
- Kein Recovery durch erneutes Setzen von `is_searchable = TRUE` ohne `ReindexGovernanceService`.
- Kein Recovery durch manuelles Setzen von `lifecycle_status` ohne Lifecycle-Service und Truth-Test.

---

## 4. Degraded-State-Regeln

Ein degradierter Zustand ist kein Fehler — er ist ein explizit dokumentierter Betriebsmodus mit bekannten Einschränkungen und einem Eskalationspfad zurück zum Normalzustand.

### 4.1 Degraded-State-Typen

| Zustand | Bedeutung | Sichtbarkeit |
|---|---|---|
| `search_degraded` | Search liefert reduzierte Ergebnisse wegen Drift oder Index-Problemen | API-Response-Header oder strukturiertes Log-Event |
| `retrieval_degraded` | Retrieval-Fenster reduziert; Citation-Completeness unter Schwelle | `chat_retrieval_completed`-Event mit `degraded: true` |
| `queue_degraded` | Dead-Letter-Wachstum oder Starvation eines Workspaces | `m5_dead_letter_growth > 0` + Alert |
| `backup_degraded` | Letztes Backup älter als Warn-Schwelle oder Verify fehlgeschlagen | `m5_backup_freshness_seconds > SLA-Warn` + Alert |
| `drift_degraded` | Drift-Score > 0 ohne abgeschlossene Repair | `m5_drift_score > 0` + Drift-Report |
| `restore_degraded` | Restore-Verifikation fehlgeschlagen oder veraltet | `m5_restore_success_rate < 1.0` + Alert |
| `llm_degraded` | LLM nicht erreichbar; RAG-Pfad nicht nutzbar | HTTP 503 + `LLM_UNAVAILABLE` |

### 4.2 Degraded-State-Regeln

- Jeder degradierte Zustand hat einen maschinenlesbaren Status (`watch`, `fail`, `blocked`).
- Kein degradierter Zustand darf als `pass` dokumentiert werden.
- Der Übergang von `degraded` zu `ok` erfordert ein aktuelles maschinenlesbares Artefakt — keine Textkorrektur.
- Degraded States werden nicht still geheilt; sie bleiben sichtbar bis zur expliziten Verifikation.
- Ein `llm_degraded`-Zustand führt zu keinem Fallback auf synthetische oder gecachte Antworten.

### 4.3 Degraded-State-Eskalation

```
Degraded State erkannt
  → Status im Report: watch / fail / blocked
  → SLA-Schwelle aus operational-sla-framework.md bestimmen
  → falls kritisch: Blocksignal aktivieren (keine Merge/Mutation)
  → Runbook einleiten
  → Recovery ausführen (Abschnitt 3)
  → Verifikation: aktueller Report mit Status ok
  → Blocksignal aufheben
  → Dokumentation aktualisieren
```

---

## 5. Strukturiertes Fehler-Logging

Jedes Fehlerereignis im Hintergrundpfad hat ein einheitliches Format.

### 5.1 Pflichtfelder

```json
{
  "event_name": "...",
  "timestamp": "ISO8601",
  "error_code": "...",
  "error_class": "...",
  "workspace_id": "...",
  "job_id": "...",
  "job_type": "...",
  "attempt": 1,
  "status_transition": "running → retryable",
  "recoverable": true,
  "degraded_state": null
}
```

Verbotene Felder (nie in Fehler-Logs):

- Dokumenttext, Chunk-Inhalt, Query-Text
- Benutzer-Passwörter, Tokens, Secrets
- Freie Nutzeridentitäten in aggregierten Events

### 5.2 Fehler-Event-Typen

| Event | Trigger |
|---|---|
| `job_failed` | Job endet mit Fehler, verbleibt in `retryable` |
| `job_dead_lettered` | Job hat maximale Retries erreicht; Status = `dead_letter` |
| `job_replay_initiated` | Admin-Aktion Replay; explizit ausgelöst |
| `recovery_started` | Explizite Recovery-Aktion begonnen |
| `recovery_completed` | Recovery abgeschlossen, Verifikation ausstehend | Quelle: `reports/current/masterplan_status.json`.
| `recovery_failed` | Recovery fehlgeschlagen; Status = `blocked` |
| `degraded_state_entered` | System wechselt in degradierten Betrieb |
| `degraded_state_resolved` | Degradierter Zustand aufgelöst, Verifikation bestanden | Quelle: `reports/current/masterplan_status.json`.
| `implicit_correction_blocked` | Versuch einer impliziten Datenkorrektur blockiert |

---

## 6. Verbotene Muster

| Muster | Verboten weil |
|---|---|
| `except Exception: pass` | verdeckt jeden Fehler |
| `except Exception: logger.debug(...)` | Fehler bleibt unsichtbar für Monitoring |
| Job-Status auf `pending` zurücksetzen ohne Retry-Zähler erhöhen | erzeugt unbegrenzte Retry-Schleife |
| `UPDATE documents SET lifecycle_status = 'active'` außerhalb Lifecycle-Service | implizite Datenkorrektur ohne Audit |
| HTTP 200 bei partiell fehlgeschlagenem Batch | verdeckt Teilfehler |
| `if retrieval_failed: return cached_answer` ohne Client-Signal | verdeckter Fallback |
| `search_vector` in INSERT/UPDATE | implizite Überschreibung eines generierten Felds |
| Alembic `downgrade: pass` ohne IRREVERSIBLE-Kommentar | verdeckt irreversible Datenverluste |
| Admin-Aktion ohne `dry_run_only=True` als Default | mutierende Aktionen ohne explizite Bestätigung |

---

## 7. Kurzcheckliste

```
[ ] Jeder Fehler erzeugt ein strukturiertes Log-Event
[ ] Jeder Job-Fehler setzt Status explizit (failed / retryable / dead_letter)
[ ] Retry-Versuche gezählt und begrenzt
[ ] Keine impliziten Datenkorrekturen ohne Audit-Spur
[ ] Partielle Ergebnisse als 207 oder explizite Fehlerliste
[ ] Kein Fallback ohne Client-sichtbaren Signal
[ ] Degraded States maschinenlesbar dokumentiert (watch / fail / blocked)
[ ] Fehlercodes in errors.py registriert, kein Code doppelt
[ ] Recovery explizit initiiert, nicht automatisch geheilt
[ ] Nach Recovery: maschinenlesbares Verifikationsartefakt
[ ] Verbotene Felder (Dokumenttext, Tokens) nicht in Fehler-Logs
```
