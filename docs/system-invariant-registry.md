# System Invariant Registry

Stand: 2026-05-13

## Ziel

Eine Invariante ist eine Bedingung, die zu jedem Zeitpunkt gilt — vor und nach jeder Operation, vor und nach jeder Migration, vor und nach jedem Restore. Verletzungen sind keine Warnungen: sie sind Gate-Blocker.

Diese Registry ist die einzige kanonische Quelle für Systeminvarianten. Sie verweist auf Tests und Gates, aber ist selbst nicht Gate — nur die maschinenlesbaren Reports sind Gate.

Verwandte Dokumente:

- `docs/data-model-invariants.md` — INV-001 bis INV-020: Dokumentmodell (Document, DocumentVersion, Chunk)
- `docs/operational-truth-governance.md` — Gate-Policies und Truth-Quellen
- `docs/retrieval-stability-contract.md` — Retrieval-Vertragsgarantien
- `docs/controlled-failure-philosophy.md` — Fehlerprinzipien und Recovery
- `docs/audit-trail-schema.md` — Audit-Trail-Pflichten

---

## 1. Invarianten-Klassen

| Klasse | Bedeutung | Gate-Implikation |
|---|---|---|
| CRITICAL | Verletzung erzeugt Datenverlust, Datenleak oder Systemkorruption | Merge-Blocker; sofortiger Stop aller mutativen Operationen |
| HIGH | Verletzung untergräbt Betriebsgarantien ohne sofortigen Datenverlust | Merge-Blocker; keine Weiterentwicklung bis Fix |
| MEDIUM | Verletzung beeinträchtigt Qualität oder Vollständigkeit | Follow-up-Pflicht im selben Sprint |

---

## 2. Dokumentmodell-Invarianten (Referenz)

Die Invarianten INV-001 bis INV-020 sind vollständig in `docs/data-model-invariants.md` definiert. Hier nur die Kurzreferenz für die Klassen-Zuordnung:

| ID | Kurzbeschreibung | Klasse | DB-Absicherung |
|---|---|---|---|
| INV-001 | Lesbares Dokument hat min. eine Version | HIGH | teilweise |
| INV-002 | `current_version_id` zeigt auf eigene Version | HIGH | teilweise |
| INV-003 | Version gehört genau einem Dokument | HIGH | ja |
| INV-004 | `version_number` eindeutig pro Dokument | HIGH | ja |
| INV-005 | Versionnummern positiv und monoton | MEDIUM | teilweise |
| INV-006 | `content_hash` eindeutig pro Workspace | HIGH | ja |
| INV-007 | Chunk gehört genau einer Version | HIGH | ja |
| INV-008 | Chunk gehört zum gleichen Dokument wie seine Version | HIGH | ja |
| INV-009 | `chunk_index` eindeutig pro Version | HIGH | ja |
| INV-010 | Chunk-Positionen nicht negativ, stabil sortierbar | MEDIUM | ja |
| INV-011 | Chunk-Anker eindeutig pro Version | HIGH | ja |
| INV-012 | `chunked`-Dokument hat min. einen Chunk | HIGH | Service |
| INV-013 | Chunk-Inhalt nicht leer | MEDIUM | ja |
| INV-014 | `source_anchor` folgt normalisiertem Schema | MEDIUM | Service |
| INV-015 | `import_status` aus erlaubter Wertemenge | HIGH | ja |
| INV-016 | `parsed`/`chunked` Dokumente haben aktuelle Version | HIGH | Service |
| INV-017 | `failed`/`pending` dürfen ohne Version existieren | — | Konvention |
| INV-018 | `updated_at >= created_at` | MEDIUM | fehlt |
| INV-019 | `version.created_at >= document.created_at` | MEDIUM | fehlt |
| INV-020 | `markdown_hash` nicht leer | MEDIUM | ja |

---

## 3. Retrieval-Invarianten

### INV-021: Archivierte Dokumente erscheinen nie in neuen Retrieval-Ergebnissen

**Beschreibung**: Search und Chat Retrieval dürfen keine Chunks liefern, deren Dokument `lifecycle_status = 'archived'` oder `is_searchable = FALSE` hat. Historische Citations auf archivierte Dokumente bleiben gültig, erzeugen aber keine neuen Treffer.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- `reports/m5_retrieval/latest.json`: `lifecycle_exclusion_violations = 0`
- postgres_truth: `test_m4c_lifecycle_retrieval_truth.py::test_m4c_archive_excludes_document_from_search_restore_reactivates`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4c_lifecycle_retrieval_truth.py
```
Gate-Bedingung: `lifecycle_exclusion_violations = 0`; jeder Wert > 0 blockiert Merge.

**Repair-Strategie**:
1. Drift-Report auswerten: `stale_rate` und `orphan_rate` prüfen
2. `ReindexGovernanceService.run_governed_reindex()` mit Scope `workspace`
3. Post-Reindex: `lifecycle_ok = true` im Reindex-Audit
4. Retrieval-Benchmark erneut ausführen: `lifecycle_exclusion_violations = 0`

---

### INV-022: Gelöschte Dokumente erscheinen nie neu

**Beschreibung**: Dokumente mit `lifecycle_status = 'deleted'` oder `deleted_at IS NOT NULL` erscheinen weder in Search noch in Chat Retrieval. `deleted`-Dokumente können nicht reaktiviert werden (kein `deleted → active`-Übergang außer über expliziten Restore aus Backup).

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- postgres_truth: `test_m4c_lifecycle_retrieval_truth.py`
- `test_cleanup_governance_truth.py`: Cleanup schützt aktive Daten

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4c_lifecycle_retrieval_truth.py
pytest -m postgres_truth backend/tests/postgres_truth/test_cleanup_governance_truth.py
```

**Repair-Strategie**:
1. Wenn gelöschtes Dokument in Search erscheint: sofortiger Reindex-Lauf
2. Wenn `deleted_at IS NOT NULL` aber `is_searchable = TRUE`: Repair-Migration Klasse C
3. `test_m4c_lifecycle_retrieval_truth.py` muss nach Repair grün sein

---

### INV-023: Retrieval-Ergebnisse sind workspace-isoliert

**Beschreibung**: Kein Search- oder Chat-Retrieval-Ergebnis darf Chunks aus einem anderen Workspace liefern. Die Workspace-Grenze ist eine Sicherheitsgrenze, nicht nur eine Filterpräferenz.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- postgres_truth: `test_m4a_auth_workspace_truth.py::test_m4a_user_a_cannot_search_workspace_b`
- `test_m4a_auth_workspace_truth.py::test_m4a_manipulated_x_workspace_id_is_forbidden`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4a_auth_workspace_truth.py
```
Gate-Bedingung: alle Workspace-Isolation-Tests grün; kein Cross-Workspace-Leak.

**Repair-Strategie**: Cross-Workspace-Leak ist ein Sicherheitsvorfall. Keine Code-Änderung ohne Security Review. Gate bleibt `blocked` bis vollständige Root-Cause-Analyse abgeschlossen ist.

---

### INV-024: Search und Chat verwenden dieselbe fachliche Sichtbarkeit

**Beschreibung**: Chat darf keine Chunks zitieren, die Search für dieselbe Query und denselben Workspace wegen Lifecycle oder Isolation ausschließt. Unterschiedliche Ranking-Logik ist erlaubt; unterschiedliche Sichtbarkeit ist verboten.

**Kritikalität**: HIGH

**Nachweisquelle**:
- `reports/m5_retrieval/latest.json`: Feld `search_chat_divergence_violations`
- `docs/retrieval-stability-contract.md` Abschnitt 1.7

**Truth-Test**: kein dedizierter postgres_truth-Test; wird über Retrieval-Benchmark-Regression abgedeckt.

**Repair-Strategie**: Lifecycle-Filter in Chat-Retrieval-Pfad gegen Search-Pfad abgleichen; Divergenz dokumentieren oder beheben.

---

## 4. Citation-Invarianten

### INV-025: Citation-Snapshots bleiben stabil

**Beschreibung**: Einmal erstellte Citations dürfen nicht nachträglich verändert werden. `chat_citations.quote_preview`, `chunk_id`, `source_anchor` und `document_id` sind nach dem Schreiben unveränderlich. Auch wenn das referenzierte Dokument archiviert oder gelöscht wird, bleibt die Citation-Zeile unverändert.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- postgres_truth: `test_citation_longevity_truth.py::test_longevity_clean_state_ok`
- Citation-Longevity-Service-Audit-Report

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_citation_longevity_truth.py
```
Gate-Bedingung: `deleted_not_marked_count = 0`; `total_drift_count = 0`.

**Repair-Strategie**:
1. Longevity-Report auswerten: `deleted_not_marked` und `restored_not_marked`
2. `source_status`-Lookup neu synchronisieren (read-only, keine Mutation der Citation)
3. Jede Schemaänderung an `chat_citations` ist Klasse D

---

### INV-026: `source_status`-Lookup ist korrekt und aktuell

**Beschreibung**: `chat_citations.source_status` reflektiert den Live-Zustand des referenzierten Dokuments (`active`, `archived`, `deleted`, `missing`). Der Wert darf sich ändern — aber nur durch den autorisierten Citation-Longevity-Service, nie durch direkte UPDATE-Statements.

**Kritikalität**: HIGH

**Nachweisquelle**:
- `test_citation_longevity_truth.py`: Testsequenz archive → delete → restore
- `m5_orphan_growth_rate`: Wachstum von orphan Citations

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_citation_longevity_truth.py -k "archived or deleted or restored"
```

**Repair-Strategie**: `CitationLongevityAuditService.run_audit()` ausführen; Report auswerten; kein direktes UPDATE auf `chat_citations.source_status`.

---

## 5. Queue-Invarianten

### INV-027: Kein Job wird mehr als einmal verarbeitet

**Beschreibung**: Ein Job im Zustand `running` wird von genau einem Worker beansprucht. Advisory-Lock-Mechanismus verhindert parallele Verarbeitung desselben Jobs. Ein Job, der abgeschlossen ist (`completed`, `failed`, `dead_letter`), wird nicht erneut gestartet — nur ein expliziter Replay erzeugt einen neuen Job.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- postgres_truth: `test_m4b_upload_queue_truth.py`
- `test_m4_crash_recovery_truth.py`: Recovery nach Crash ohne Doppelverarbeitung

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4b_upload_queue_truth.py
pytest -m postgres_truth backend/tests/postgres_truth/test_m4_crash_recovery_truth.py
```

**Repair-Strategie**:
1. Advisory-Lock-State prüfen: kein Lock-Leak nach Crash
2. `running`-Jobs mit abgelaufenem Timeout identifizieren
3. Recovery-Pfad aus `docs/controlled-failure-philosophy.md` Abschnitt 3.1 (Advisory-Lock-Recovery)

---

### INV-028: Dead-Letter-Jobs werden nicht still ignoriert

**Beschreibung**: Jeder Job, der die maximale Retry-Anzahl erreicht, wechselt deterministisch nach `dead_letter`. `dead_letter`-Jobs verbleiben sichtbar in der Queue und erzeugen ein Audit-Event. Sie werden nicht gelöscht, bis ein expliziter Replay oder eine explizite Archivierung erfolgt.

**Kritikalität**: HIGH

**Nachweisquelle**:
- `m5_dead_letter_growth`: Wachstum > 0 = Warnsignal
- `test_queue_aging_truth.py::test_aging_dead_letter_warning_threshold`
- `test_queue_aging_truth.py::test_aging_dead_letter_critical_threshold`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_queue_aging_truth.py -k "dead_letter"
```

**Repair-Strategie**: Replay via Admin-API mit explizitem Audit-Event; nie direkt `DELETE FROM background_jobs WHERE status = 'dead_letter'` ohne Replay-Prüfung.

---

### INV-029: Queue-Jobs sind workspace-isoliert

**Beschreibung**: Ein User kann keine Jobs anderer Workspaces lesen, starten oder replayen. Die Workspace-Grenze gilt auch für Queue-Zugriff via Admin-API.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- `test_m4a_auth_workspace_truth.py::test_m4a_user_a_cannot_read_or_replay_workspace_b_queue_job`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4a_auth_workspace_truth.py -k "queue"
```

**Repair-Strategie**: Wie INV-023 — Cross-Workspace-Leak ist Sicherheitsvorfall.

---

## 6. Workspace-Isolations-Invarianten

### INV-030: Workspace-Grenzen gelten für alle Datenzugriffe

**Beschreibung**: Dokumente, Versionen, Chunks, Jobs, Chat-Sessions und Citations sind an eine `workspace_id` gebunden. Kein API-Endpunkt darf workspace-fremde Daten zurückgeben. Manipulierte `X-Workspace-Id`-Header werden als verboten behandelt.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- postgres_truth: vollständige `test_m4a_auth_workspace_truth.py`-Suite
- `test_m4a_auth_workspace_truth.py::test_m4a_manipulated_x_workspace_id_is_forbidden`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4a_auth_workspace_truth.py
```
Gate-Bedingung: alle 11 Tests grün; kein Skip.

**Repair-Strategie**: Sicherheitsvorfall-Protokoll; kein Merge bis vollständige Isolation-Analyse abgeschlossen.

---

### INV-031: Admin-Aktionen erfordern explizite Workspace-Zugehörigkeit

**Beschreibung**: Admin-Endpunkte, die workspace-scoped Daten mutieren, benötigen explizite Workspace-Verifizierung (Admin- oder Owner-Rolle im betroffenen Workspace). Globale Admin-Aktionen dürfen workspace-scoped Daten nur aggregiert, nie im Klartext zurückgeben.

**Kritikalität**: HIGH

**Nachweisquelle**:
- `test_m4a_auth_workspace_truth.py::test_m4a_admin_diagnostics_without_admin_role_is_forbidden`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_m4a_auth_workspace_truth.py -k "admin"
```

**Repair-Strategie**: Auth-Gate in Admin-Endpunkt nachrüsten; kein Merge ohne bestandenen Auth-Gate-Test.

---

## 7. Restore-Invarianten

### INV-032: Restore erzeugt keine verwaisten Daten

**Beschreibung**: Nach einem vollständigen Restore in eine leere Zieldatenbank existieren keine Orphan-Chunks (Chunks ohne Version), keine Orphan-Versionen (Versionen ohne Dokument) und keine verwaisten Citations (Citations mit ungültigem Dokument- oder Chunk-Verweis).

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- Restore-Truth-Report: `orphan_chunks = 0`, `orphan_versions = 0`, `orphan_citations = 0`
- `BackupRestoreService.verify_backup()`: `ok = true`
- `m5_orphan_growth_rate = 0` nach Restore

**Truth-Test**:
```
# Restore-Truth-Lauf (manuell, gegen echte PostgreSQL):
python scripts/validate_restore_truth.py
```
Gate-Bedingung: `verify_backup()` gibt OK; INV-001 bis INV-020 gelten nach Restore.

**Repair-Strategie**:
1. Orphan-Chunks: `ReindexGovernanceService` nach Restore ausführen
2. Orphan-Versionen: Daten-Inventar mit `migration_document_repairs`-Logik
3. Orphan-Citations: `CitationLongevityAuditService` nach Restore ausführen
4. Falls Orphans persistieren: Backup-Manifest auf Vollständigkeit prüfen

---

### INV-033: Alembic-Head nach Restore konsistent

**Beschreibung**: Nach `alembic upgrade head` auf einer Restore-Ziel-DB existiert genau ein Alembic-Head (kein Split-Head). Migrations-Chain ist lückenlos vom ältesten unterstützten Backup bis zum aktuellen Head.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- `reports/postgres_truth_report.json`: `alembic_heads` enthält genau eine Revision
- `alembic heads` gibt genau eine Zeile zurück

**Truth-Test**:
```
cd backend
alembic heads   # muss genau 1 Revision zeigen
pytest -m postgres_truth backend/tests/postgres_truth/ -q
```
Gate-Bedingung: `alembic_heads` im Report = 1 Eintrag; `failed = 0`.

**Repair-Strategie**: Merge-Migration erstellen (`alembic merge`); postgres_truth-Lauf nach Merge; kein Split-Head erlaubt.

---

### INV-034: Backup-Manifest ist vollständig und verifiziert

**Beschreibung**: Ein Backup gilt nur als valide, wenn das Manifest alle restore-relevanten Artefakte enthält (DB-Dump, technische Dateien, `alembic_heads`) und `verify_backup()` `ok = true` zurückgibt. Ein unverifiziertes Backup ist kein valides Backup.

**Kritikalität**: HIGH

**Nachweisquelle**:
- `m5_backup_freshness_seconds`: Alter seit `verified_at`
- Restore-Truth-Report: `verify_passed = true`

**Truth-Test**: `BackupRestoreService.verify_backup()` mit aktuellem Backup-Manifest.

**Repair-Strategie**: Backup-Lauf wiederholen; Verify-Lauf forcieren; bis Verify bestanden: kein destructiver Betrieb (Klasse-D-Migrationen, Cleanup-Mutation).

---

## 8. Entropy- und Drift-Invarianten

### INV-035: `STALE_RATE_MAX` und `ORPHAN_RATE_MAX` nicht überschritten

**Beschreibung**: Der Anteil staler Index-Einträge (`is_searchable = TRUE` für archivierte/gelöschte Dokumente) und verwaister Chunks darf die konfigurierten Schwellen nicht dauerhaft überschreiten.

**Kritikalität**: HIGH

**Nachweisquelle**:
- `reports/m5_entropy/latest.json`: `stale_rate`, `orphan_rate`
- `test_entropy_truth.py`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_entropy_truth.py
```
Gate-Bedingung: `stale_rate ≤ STALE_RATE_MAX`; `orphan_rate ≤ ORPHAN_RATE_MAX`; `retrieval_coverage ≥ RETRIEVAL_COVERAGE_MIN`.

**Repair-Strategie**: `ReindexGovernanceService` für stale entries; Cleanup-Dry-Run für Orphans; beide mit Audit-Trail.

---

### INV-036: `RETRIEVAL_COVERAGE_MIN` eingehalten

**Beschreibung**: Mindestens `RETRIEVAL_COVERAGE_MIN = 0.85` aller aktiven, nicht-archivierten Dokument-Chunks müssen searchable sein (`is_searchable = TRUE`). Unterschreitung bedeutet systemische Indexkorruption.

**Kritikalität**: CRITICAL

**Nachweisquelle**:
- `reports/m5_entropy/latest.json`: `retrieval_coverage`
- `test_entropy_truth.py`

**Truth-Test**:
```
pytest -m postgres_truth backend/tests/postgres_truth/test_entropy_truth.py -k "coverage"
```

**Repair-Strategie**: Vollständiger Reindex über `ReindexGovernanceService`; Lifecycle-Inkonsistenz-Check im Post-Reindex-Report; Retrieval-Benchmark nach Repair.

---

## 9. GUI-State-Invarianten

### INV-037: Keine Workspace-Daten ohne validierten Workspace

**Beschreibung**: Dokumentlisten, Search-Ergebnisse, Chat-Sessions, Chat-Details und Upload-Controls duerfen nur gerendert oder ausgeloest werden, wenn die Auth-Session einen validierten `active_workspace_id` besitzt und dieser Workspace in den Memberships enthalten ist.

**Kritikalitaet**: CRITICAL

**Nachweisquelle**:
- Unit: `frontend/src/tests/auth/StateInvariants.test.js`
- Component: `frontend/src/tests/app/GuiStateInvariants.test.jsx`
- E2E: `frontend/tests/gui_truth/test_11_state_invariants.spec.js`

**Truth-Test**:
```
cd frontend
npm test -- --run src/tests/auth/StateInvariants.test.js src/tests/app/GuiStateInvariants.test.jsx
npx playwright test --config=playwright.config.js tests/gui_truth/test_11_state_invariants.spec.js
```

**Repair-Strategie**: Guard in `ProtectedRoute` und `hasValidatedWorkspace()` wiederherstellen; keine Page darf ProtectedRoute umgehen.

---

### INV-038: Auth-Fehler loeschen sensitive GUI-States

**Beschreibung**: `AUTH_REQUIRED`/401 darf keine zuvor geladenen Dokumente, Suchbegriffe, Treffer, Chat-Inhalte oder Upload-Zustaende sichtbar lassen. Der Auth-Kontext und API-Kontext werden geleert; geschuetzte Seiten unmounten.

**Kritikalitaet**: CRITICAL

**Nachweisquelle**:
- Component: `GuiStateInvariants.test.jsx::clears sensitive document state after AUTH_REQUIRED`
- E2E Auth-Logout/Invalid-Token-Flows in `test_02_auth_bootstrap.spec.js`

**Repair-Strategie**: `setOnAuthRequired()` muss Auth-State und API-Request-Kontext zentral leeren; geschuetzte Pages duerfen sensitive State nicht ausserhalb ihres Komponenten-Lifecycles persistieren.

---

### INV-039: Workspace-Wechsel loescht alte workspace-bezogene GUI-States

**Beschreibung**: Beim Wechsel des aktiven Workspace werden Dokumentliste neu geladen, Search-State und Upload-State geleert und Chat-Detail-URLs auf `/chat` zurueckgesetzt. Alte Treffer oder Upload-Jobs duerfen nicht als Zustand des neuen Workspace erscheinen.

**Kritikalitaet**: HIGH

**Nachweisquelle**:
- Component: `GuiStateInvariants.test.jsx::resets old workspace search and upload state on workspace switch`
- E2E: `test_10_workspace_bootstrap.spec.js`, `test_11_state_invariants.spec.js`

**Repair-Strategie**: Workspace-ID in alle page-scoped Effects aufnehmen; transiente States in einem `useEffect([workspaceId])` zuruecksetzen.

---

### INV-040: Kontrollierte API-Fehler erzeugen keine falschen GUI-Zustaende

**Beschreibung**: `API_UNREACHABLE` wird als Fehlerzustand gerendert und darf keinen Empty-State vortaeuschen. `FORBIDDEN` ist nicht retryable und darf keinen Retry-Loop oder Retry-Button erzeugen.

**Kritikalitaet**: HIGH

**Nachweisquelle**:
- Component: `GuiStateInvariants.test.jsx`
- E2E: `test_11_state_invariants.spec.js`
- API Client: `ClientErrors.test.js`

**Repair-Strategie**: Fehlerklassifikation im zentralen API-Client stabil halten; Retry-Aktionen nur fuer `API_UNREACHABLE` und `TIMEOUT` freischalten.

---

## 10. Gate-Mapping

| Invariante | Gate | Pflichttest | Stop-Signal |
|---|---|---|---|
| INV-021 | Retrieval-Gate | `test_m4c_lifecycle_retrieval_truth.py` | `lifecycle_exclusion_violations > 0` |
| INV-022 | Retrieval-Gate | `test_m4c_lifecycle_retrieval_truth.py` | gelöschtes Dokument in Search |
| INV-023 | Auth/Isolation-Gate | `test_m4a_auth_workspace_truth.py` | Cross-Workspace-Daten in Response |
| INV-024 | Retrieval-Gate | Retrieval-Benchmark | `search_chat_divergence_violations > 0` |
| INV-025 | Citation-Gate | `test_citation_longevity_truth.py` | `total_drift_count > 0` |
| INV-026 | Citation-Gate | `test_citation_longevity_truth.py` | `deleted_not_marked_count > 0` |
| INV-027 | Queue-Gate | `test_m4b_upload_queue_truth.py` | Doppelverarbeitung erkannt |
| INV-028 | Queue-Gate | `test_queue_aging_truth.py` | `dead_letter_growth > 0` ohne Audit |
| INV-029 | Auth/Isolation-Gate | `test_m4a_auth_workspace_truth.py` | Queue-Cross-Workspace-Leak |
| INV-030 | Auth/Isolation-Gate | `test_m4a_auth_workspace_truth.py` | alle 11 Tests, kein Skip |
| INV-031 | Auth/Isolation-Gate | `test_m4a_auth_workspace_truth.py` | Admin ohne Workspace-Auth |
| INV-032 | Restore-Gate | Restore-Truth-Lauf | `orphan_count > 0` nach Restore |
| INV-033 | Restore-Gate + M4-Gate | `alembic heads` + postgres_truth | Split-Head oder `failed > 0` |
| INV-034 | Restore-Gate | `verify_backup()` | `ok = false` |
| INV-035 | Entropy-Gate | `test_entropy_truth.py` | Rate > Schwelle |
| INV-036 | Entropy-Gate | `test_entropy_truth.py` | Coverage < 0.85 |
| INV-037 | GUI-State-Gate | `StateInvariants.test.js`, `GuiStateInvariants.test.jsx`, `test_11_state_invariants.spec.js` | Workspace-Daten ohne validierten Workspace |
| INV-038 | GUI-State-Gate | `GuiStateInvariants.test.jsx` | Sensitive State nach Auth-Fehler sichtbar |
| INV-039 | GUI-State-Gate | `test_10_workspace_bootstrap.spec.js`, `GuiStateInvariants.test.jsx` | Alter Workspace-State nach Wechsel sichtbar |
| INV-040 | GUI-Recovery-Gate | `ClientErrors.test.js`, `GuiStateInvariants.test.jsx` | Fake-Empty-State oder Retry-Loop |

---

## 11. Kurzcheckliste

```
[ ] INV-001 bis INV-020 (data-model-invariants.md) nach jeder Migration geprüft
[ ] INV-021/022 (Retrieval-Filterung): lifecycle_exclusion_violations = 0
[ ] INV-023/029/030 (Workspace-Isolation): alle Isolation-Tests grün
[ ] INV-025/026 (Citation-Stabilität): total_drift_count = 0
[ ] INV-027 (Queue-Idempotenz): kein Doppelverarbeitungs-Signal
[ ] INV-028 (Dead-Letter): dead_letter_growth = 0 oder mit Audit
[ ] INV-032 (Restore-Orphans): orphan_count = 0 nach Restore
[ ] INV-033 (Alembic-Head): genau 1 Head nach Restore
[ ] INV-035/036 (Entropy): stale_rate/orphan_rate ≤ Max; coverage ≥ 0.85
[ ] INV-037 bis INV-040 (GUI-State): kein Ghost-Workspace, kein Fake-Empty-State, kein FORBIDDEN-Retry
[ ] Alle CRITICAL-Invarianten vor jedem Milestone-Gate geprüft
[ ] Neue Invarianten bei neuen Features in diese Registry eingetragen
```
