# Audit Trail Schema

Stand: 2026-05-13

## Ziel

Jede auditpflichtige Aktion hinterlässt ein vollständiges, maschinenlesbares Protokoll. Der Audit-Trail ist keine optionale Begleitdokumentation — er ist Governance-Pflicht und Gate-Voraussetzung für alle mutativen Operationen.

Verwandte Dokumente:

- `docs/controlled-failure-philosophy.md` — Fehlerprinzipien und Recovery
- `docs/operational-truth-governance.md` — Truth-Quellen und Gate-Policies
- `docs/architecture-change-governance.md` — Change-Control-Prozess
- `backend/app/observability/logging.py` — `log_event`-Implementierung
- `backend/app/services/reindex_governance.py` — Reindex-Audit-Referenzimplementierung
- `backend/app/services/cleanup_governance.py` — Cleanup-Audit-Referenzimplementierung

---

## 1. Auditpflichtige Ereignistypen

Die folgenden Operationen sind ohne vollständigen Audit-Trail verboten:

| Nr. | Ereignis | Scope |
|---|---|---|
| A1 | Reindex | Workspace / Global |
| A2 | Cleanup | Workspace |
| A3 | Restore | Global |
| A4 | Dead-Letter Replay | Workspace |
| A5 | Lifecycle-Wechsel | Dokument |
| A6 | Drift Repair | Workspace / Global |
| A7 | Schema-Migration | Global |
| A8 | Admin-Aktion | Workspace / Global |

Eine Operation ohne Audit-Event ist ein Governance-Verstoß und gilt als blockierend für das zugehörige Gate.

---

## 2. Basis-Audit-Schema

Jedes Audit-Event muss alle Pflichtfelder enthalten. Fehlende Pflichtfelder machen das Event ungültig.

### 2.1 Pflichtfelder

```json
{
  "event_name": "string — kanonischer Eventname, z.B. reindex_governance_started",
  "event_version": "1",
  "timestamp": "ISO 8601 UTC — Zeitpunkt des Events",
  "correlation_id": "UUID — verbindet Start-, Abschluss- und Fehler-Events einer Operation",
  "actor": {
    "type": "system | admin | migration | scheduler",
    "id": "string — User-ID, Job-ID oder 'system'",
    "role": "string — owner | admin | system | migration"
  },
  "workspace_id": "string | null — null nur bei globalen Operationen",
  "operation": "string — Operationstyp, z.B. reindex | cleanup | restore",
  "operation_scope": "string — full | workspace | document | global",
  "status": "started | completed | failed | rolled_back",
  "state_before": {},
  "state_after": {},
  "result": {},
  "error": null
}
```

### 2.2 Felddefinitionen

**`correlation_id`**: UUID, generiert beim Start der Operation. Alle Events einer Operation (Start, Abschluss, Fehler) tragen dieselbe `correlation_id`. Ermöglicht vollständige Rekonstruktion einer Operationskette.

**`actor`**: Wer hat die Operation ausgelöst?
- `system`: automatischer Scheduler oder Governance-Service
- `admin`: menschliche Admin-Aktion via API
- `migration`: Alembic-Migration
- `scheduler`: Hintergrund-Worker

**`state_before` / `state_after`**: maschinenlesbarer Zustandsschnappschuss vor und nach der Operation. Format ist operationsspezifisch (Abschnitt 3). Beide Felder sind Pflicht; fehlt `state_after` bei Fehlern, muss `state_after: null` mit Begründung im `error`-Feld dokumentiert sein.

**`error`**: null bei Erfolg. Bei Fehler:
```json
{
  "code": "IMPORT_FAILED",
  "class": "ImportFailedApiError",
  "message": "...",
  "recoverable": true,
  "recovery_action": "retry | rollback | manual"
}
```

### 2.3 Verbotene Felder

Audit-Events dürfen nie enthalten:
- Dokumenttext, Chunk-Inhalt, Query-Text
- Passwörter, API-Tokens, Secrets
- Freie Nutzeridentitäten in aggregierten Events
- Stack-Traces in Produktions-Audit-Logs

---

## 3. Eventmodell je Operationstyp

### A1: Reindex

Kanonische Events: `reindex_governance_started`, `reindex_governance_completed`

```json
{
  "event_name": "reindex_governance_completed",
  "event_version": "1",
  "timestamp": "2026-05-13T10:00:00Z",
  "correlation_id": "uuid-v4",
  "actor": { "type": "admin", "id": "user-uuid", "role": "owner" },
  "workspace_id": "ws-uuid",
  "operation": "reindex",
  "operation_scope": "workspace",
  "status": "completed",
  "state_before": {
    "drift_score": 3,
    "drift_severity": "medium",
    "stale_count": 12,
    "orphan_count": 2
  },
  "state_after": {
    "drift_score": 0,
    "drift_severity": "none",
    "stale_count": 0,
    "orphan_count": 0
  },
  "result": {
    "duration_ms": 1240,
    "reindex_type": "workspace",
    "drift_delta": -3,
    "lifecycle_ok": true,
    "regression_check_required": true
  },
  "error": null
}
```

### A2: Cleanup

Kanonische Events: `cleanup_governance_started`, `cleanup_governance_completed`

```json
{
  "event_name": "cleanup_governance_completed",
  "state_before": {
    "orphan_chunk_count": 8,
    "stale_version_count": 3,
    "candidate_count": 11
  },
  "state_after": {
    "orphan_chunk_count": 0,
    "stale_version_count": 0,
    "deleted_count": 11
  },
  "result": {
    "dry_run": false,
    "candidate_count": 11,
    "protected_count": 0,
    "blocked_count": 0,
    "deleted_count": 11,
    "citation_impact": false,
    "active_data_impact": false,
    "queue_impact": false
  },
  "error": null
}
```

**Sonderregel**: `dry_run: true` in `result` bedeutet keine Datenmutation ist erfolgt. Ein Cleanup-Audit mit `dry_run: false` und `blocked_count > 0` ist ein Governance-Verstoß.

### A3: Restore

Kanonische Events: `restore_started`, `restore_completed`, `restore_failed`

```json
{
  "event_name": "restore_completed",
  "workspace_id": null,
  "operation": "restore",
  "operation_scope": "global",
  "state_before": {
    "target_db_empty": true,
    "backup_manifest_version": "20260513_001",
    "backup_verified_at": "2026-05-12T08:00:00Z"
  },
  "state_after": {
    "alembic_head": "20260512_0016",
    "document_count": 142,
    "chunk_count": 3820,
    "truth_smoke_status": "pass",
    "reindex_after_restore": true
  },
  "result": {
    "restore_duration_seconds": 418,
    "verify_passed": true,
    "data_parity_ok": true,
    "invariants_checked": ["INV-001", "INV-002", "INV-003"]
  },
  "error": null
}
```

### A4: Dead-Letter Replay

Kanonische Events: `job_replay_initiated`, `job_replay_completed`, `job_replay_failed`

```json
{
  "event_name": "job_replay_completed",
  "actor": { "type": "admin", "id": "user-uuid", "role": "admin" },
  "state_before": {
    "job_id": "job-uuid",
    "job_type": "document_import",
    "previous_status": "dead_letter",
    "previous_attempts": 3,
    "failure_reason": "IMPORT_FAILED"
  },
  "state_after": {
    "new_job_id": "job-uuid-new",
    "status": "queued",
    "attempts": 0
  },
  "result": {
    "original_job_archived": true,
    "replay_reason": "transient DB connection failure resolved"
  },
  "error": null
}
```

### A5: Lifecycle-Wechsel

Kanonische Events: `lifecycle_transition_completed`, `lifecycle_transition_failed`

```json
{
  "event_name": "lifecycle_transition_completed",
  "actor": { "type": "admin", "id": "user-uuid", "role": "owner" },
  "workspace_id": "ws-uuid",
  "operation": "lifecycle_transition",
  "operation_scope": "document",
  "state_before": {
    "document_id": "doc-uuid",
    "lifecycle_status": "active",
    "is_searchable": true,
    "version_count": 3
  },
  "state_after": {
    "lifecycle_status": "archived",
    "is_searchable": false,
    "archived_at": "2026-05-13T10:00:00Z"
  },
  "result": {
    "transition": "active → archived",
    "citation_impact": "existing citations remain valid",
    "index_cleanup_triggered": true
  },
  "error": null
}
```

**Sonderregel**: Jeder Lifecycle-Wechsel außerhalb des Lifecycle-Service ist verboten. Das Audit-Event ist die Verifikation, dass der Wechsel über den autorisierten Pfad lief.

### A6: Drift Repair

Kanonische Events: `drift_repair_started`, `drift_repair_completed`

```json
{
  "event_name": "drift_repair_completed",
  "actor": { "type": "system", "id": "drift-repair-scheduler", "role": "system" },
  "state_before": {
    "drift_score": 7,
    "stale_rate": 0.12,
    "orphan_rate": 0.04,
    "retrieval_coverage": 0.81
  },
  "state_after": {
    "drift_score": 0,
    "stale_rate": 0.00,
    "orphan_rate": 0.00,
    "retrieval_coverage": 0.91
  },
  "result": {
    "repair_type": "reindex + orphan_cleanup",
    "duration_ms": 8420,
    "report_ref": "reports/m5_entropy/20260513_100000.json"
  },
  "error": null
}
```

### A7: Schema-Migration

Kanonische Events: `migration_started`, `migration_completed`, `migration_failed`, `migration_rolled_back`

```json
{
  "event_name": "migration_completed",
  "actor": { "type": "migration", "id": "alembic", "role": "migration" },
  "workspace_id": null,
  "operation": "schema_migration",
  "operation_scope": "global",
  "state_before": {
    "alembic_head": "20260512_0015",
    "schema_revision": "20260512_0015",
    "migration_class": "B",
    "irreversible": false
  },
  "state_after": {
    "alembic_head": "20260513_0016",
    "schema_revision": "20260513_0016",
    "downgrade_available": true
  },
  "result": {
    "migration_id": "20260513_0016",
    "migration_name": "add_entropy_baseline_table",
    "duration_ms": 340,
    "postgres_truth_run": true,
    "postgres_truth_status": "pass",
    "restore_test_required": false,
    "restore_test_status": null
  },
  "error": null
}
```

### A8: Admin-Aktion

Kanonische Events: `admin_action_started`, `admin_action_completed`, `admin_action_failed`

```json
{
  "event_name": "admin_action_completed",
  "actor": { "type": "admin", "id": "user-uuid", "role": "admin" },
  "workspace_id": "ws-uuid",
  "operation": "admin_action",
  "operation_scope": "workspace",
  "state_before": {
    "action": "trigger_reindex",
    "dry_run": false,
    "target": "workspace"
  },
  "state_after": {
    "reindex_correlation_id": "uuid-v4",
    "status": "triggered"
  },
  "result": {
    "endpoint": "POST /api/v1/admin/reindex",
    "http_status": 200,
    "safety_gate_passed": true,
    "dry_run_completed_first": true
  },
  "error": null
}
```

**Sonderregel**: Mutierende Admin-Aktionen ohne vorherigen Dry-Run-Pass sind ein Governance-Verstoß. Das Audit-Event muss `dry_run_completed_first: true` oder `dry_run: true` ausweisen.

---

## 4. Retention-Regeln

### 4.1 Aufbewahrungsfristen

| Ereignistyp | Minimale Retention | Begründung |
|---|---|---|
| Reindex | 90 Tage | Drift-Trend-Analyse über Quartale |
| Cleanup | 365 Tage | Destructive Operationen brauchen langen Audit-Horizont |
| Restore | unbegrenzt | DR-Nachweise müssen dauerhaft nachvollziehbar sein |
| Dead-Letter Replay | 90 Tage | Fehler-Muster-Analyse |
| Lifecycle-Wechsel | 365 Tage | Historische Citations referenzieren Lifecycle-Zustand |
| Drift Repair | 90 Tage | Trend-Analyse über Quartale |
| Schema-Migration | unbegrenzt | Migrations-Historie ist Teil der DB-Wahrheit |
| Admin-Aktion | 365 Tage | Compliance und Change-Nachvollziehbarkeit |

### 4.2 Retention-Invarianten

- Audit-Events dürfen nicht gelöscht werden, solange eine offene `correlation_id` existiert (kein abgeschlossenes End-Event).
- Audit-Events zu Schema-Migrationen und Restore-Operationen sind permanent — keine automatische Löschung.
- Cleanup-Audit-Events dürfen nicht durch denselben Cleanup-Prozess gelöscht werden, den sie protokollieren.
- Historische Citations referenzieren Lifecycle-Wechsel-Events; deren Retention darf nicht unter 365 Tage sinken.

### 4.3 Archivierung

- Events nach Ablauf der aktiven Retention wandern in Kalt-Archiv (append-only).
- Kalt-Archiv-Events dürfen gelesen, aber nicht modifiziert werden.
- Archiv-Zugriff wird selbst als Audit-Event protokolliert.

---

## 5. Korrelations-Regeln

### 5.1 Operationskette

Eine vollständige Operation besteht aus mindestens zwei Events:

```
correlation_id: "abc-123"
  → event: reindex_governance_started  (status: started)
  → event: reindex_governance_completed (status: completed | failed | rolled_back)
```

Eine `correlation_id` ohne End-Event nach Timeout ist ein offener Fehlerfall und wird als `blocked` gewertet.

### 5.2 Verschachtelte Operationen

Wenn eine Admin-Aktion eine Reindex-Operation auslöst, erhält die Reindex-Operation eine eigene `correlation_id`, die mit der Admin-Aktions-ID verknüpft ist:

```json
{
  "correlation_id": "reindex-uuid",
  "parent_correlation_id": "admin-action-uuid"
}
```

`parent_correlation_id` ist optional aber empfohlen für alle automatisch ausgelösten Operationen.

### 5.3 Fehlende End-Events

Wenn ein Start-Event existiert, aber kein End-Event nach dem konfigurierten Timeout:

- Status der Operation: `unknown`
- Gate-Implikation: `blocked` bis Recovery oder manuelles Abschlussevent
- Pflichtaktion: Recovery-Pfad aus `docs/controlled-failure-philosophy.md` Abschnitt 3 einleiten

---

## 6. Audit-Trail-Gates

| Gate | Bedingung |
|---|---|
| Cleanup-Gate | vollständiger Cleanup-Audit mit `blocked_count = 0` und `dry_run`-Event vor Mutation |
| Reindex-Gate | vollständiger Reindex-Audit mit `drift_delta ≤ 0` und `lifecycle_ok = true` |
| Restore-Gate | vollständiger Restore-Audit mit `verify_passed = true` und `truth_smoke_status = pass` |
| Migration-Gate | vollständiger Migration-Audit mit `postgres_truth_status = pass` |
| Admin-Aktion-Gate | vollständiger Admin-Audit mit `safety_gate_passed = true` |

Fehlt ein Audit-Event für eine abgeschlossene Gate-Operation, ist der Gate-Status `unknown`, nicht `pass`.

---

## 7. Implementierungsanker

| Komponente | Datei | Funktion |
|---|---|---|
| Log-Event-Sink | `backend/app/observability/logging.py` | `log_event()` |
| Reindex-Audit | `backend/app/services/reindex_governance.py` | `run_governed_reindex()` |
| Cleanup-Audit | `backend/app/services/cleanup_governance.py` | `run_governed_cleanup()` |
| Schema-Migrations-Audit | Alembic-Migrations-Header | Pflicht-Header-Format aus `schema-evolution-safety-model.md` |
| Actor-Kontext | API-Layer | `actor`-Feld aus Auth-Session in alle Governance-Aufrufe injizieren |

**Offene Lücke**: Das `actor`-Feld ist in den bestehenden Services (`reindex_governance.py`, `cleanup_governance.py`) noch nicht implementiert — `log_event()` enthält aktuell kein `actor`-Argument. Jede neue auditpflichtige Operation muss `actor` als Pflichtfeld übergeben; bestehende Services brauchen ein Follow-up-Issue.

---

## 8. Kurzcheckliste

```
[ ] Alle 8 auditpflichtigen Ereignistypen haben Start- und End-Event
[ ] Jedes Event enthält correlation_id, actor, timestamp, workspace_id
[ ] state_before und state_after für jede Operation vorhanden
[ ] error-Feld bei Fehler gesetzt; null bei Erfolg
[ ] Keine verbotenen Felder (Dokumenttext, Tokens, Secrets)
[ ] Retention-Fristen je Eventtyp eingehalten
[ ] Offene correlation_ids (kein End-Event) als blocked markiert
[ ] Mutierende Admin-Aktionen: dry_run_completed_first = true
[ ] Cleanup-Mutation: blocked_count = 0 im Audit nachgewiesen
[ ] Schema-Migration: postgres_truth_status = pass im Audit
[ ] Audit-Events nicht durch denselben Prozess löschbar, den sie protokollieren
```
