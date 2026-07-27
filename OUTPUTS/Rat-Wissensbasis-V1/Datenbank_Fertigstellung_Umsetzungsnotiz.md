# Datenbank-Fertigstellung — Umsetzungsnotiz

Stand: 2026-07-26. Status: **implementiert, statisch verifiziert. Live-Lauf gegen PostgreSQL steht aus.**
Nicht committet.

## Methode

Kein Ratespiel: alle 29 Migrationen wurden gegen ein Schemamodell durchgespielt
(PostgreSQL-Semantik, ohne DB — die Sandbox kann kein Postgres installieren) und
mit den ORM-Metadaten gediffed. Das Replay-Werkzeug liegt jetzt als Testmodul im
Repo, damit der Vergleich wiederholbar ist und nicht als Einmalanalyse verpufft.

## Befund vor der Aenderung

| Kategorie | Befund |
|---|---|
| Tote Tabellen | 5 Tabellen in den Migrationen, in `app/` nirgends referenziert |
| Invarianten nur in der Migration | 17 Check-Constraints, 8 Unique-Constraints/Indizes fehlten im ORM |
| Typdrift | `document_versions.metadata`, `document_chunks.metadata`/`heading_path`, `chat_messages.metadata`, `chat_citations.source_anchor`: Migration JSONB, ORM JSON |
| Echter Defekt | `background_jobs.status='cancelled'` existiert im gesamten Code, die DB verbietet ihn |
| Echter Defekt | `documents.lifecycle_status`: ORM erlaubte `'pending'`, DB und API nicht |
| Echter Defekt | `scripts/seed_auth.py` setzt `is_default=true` ohne `kind='shared'` — verletzt seit Migration 0027 den Consistency-Check |

Masterplan-Muss-Felder fuer `documents` und `document_versions` waren dagegen
vollstaendig. Da war nichts offen.

## Geaenderte Dateien

### Schema
- `backend/migrations/versions/20260726_0028_drop_dead_analysis_tables.py` (neu)
  Droppt `analysis_groups`, `analysis_group_documents`, `analysis_results_legacy`,
  `analysis_result_sources_legacy`. Bricht ab, wenn eine davon noch Zeilen
  enthaelt (`ALLOW_DROP_NONEMPTY_LEGACY=1` als bewusster Override).
  **Nicht gedroppt: `migration_document_repairs`** — das ist das Audit-Log der
  Datenreparatur aus 0010, also Nachweis, nicht Feature-Rest.
- `backend/migrations/versions/20260726_0029_background_jobs_cancelled_status.py` (neu)
  Erweitert `ck_background_jobs_status_allowed` um `'cancelled'`.

### Modelle
- `backend/app/models/documents.py` — Checks, Unique-Constraints, partielle
  Unique-Indizes und Indizes aus der Migrationskette nachgezogen;
  `json_column()` als JSON/JSONB-Variante; `lifecycle_status` auf die drei
  zulaessigen Werte korrigiert.
  `workspaces.kind` bekommt einen **abgeleiteten** Default statt `'private'`:
  die DB erzwingt `(kind='shared') <=> (is_default=true)`, also darf kind nicht
  unabhaengig geraten werden.
- `backend/app/models/analysis.py` — `uq_analysis_results_job_id` und
  `uq_analysis_comparisons_job_id` benannt statt anonym ueber `unique=True`.

### Multi-User (Story 5/6)
- `backend/app/api/v1/users.py` (neu) — `POST /api/v1/users`, `GET /api/v1/users`,
  `GET /api/v1/users/shared-workspace`, `PUT /api/v1/users/{id}/shared-role`,
  `POST /api/v1/users/{id}/deactivate`.
- `backend/app/schemas/users.py` (neu).
- `backend/app/api/v1/router.py` — Router registriert.
- `backend/scripts/seed_auth.py` — setzt `kind='shared'` und `owner_user_id=NULL`
  am Default-Workspace, in beiden Zweigen (Anlage und Update).

Rechte-Detail: `require_shared_admin` prueft die Rolle im **gemeinsamen**
Workspace, nicht im aktiven. Wer in seinem privaten Bereich `owner` ist, darf
damit noch keine Benutzer anlegen. `require_workspace_admin` waere hier falsch
gewesen.

Story 2 (Fehlercodes) war bereits umgesetzt — `USER_ALREADY_EXISTS`,
`SHARED_WORKSPACE_MISSING`, `LAST_ADMIN_PROTECTED` etc. stehen in
`app/core/errors.py`.

### Nachweis
- `backend/tests/integration/_schema_replay.py` (neu) — Replay der Kette ohne DB.
- `backend/tests/integration/test_schema_truth_0028_0029.py` (neu) —
  2 DB-freie Tests (Kette linear + ORM==Migration) als CI-Gate,
  9 `@pytest.mark.postgres`-Tests fuer die Invarianten auf echter DB.
- `OUTPUTS/Rat-Wissensbasis-V1/verify_schema_0028_0029.ps1` (neu) — Runner.

### Testfixtures korrigiert
- `backend/tests/conftest.py` — `document_fixture` legt Dokumente jetzt als
  `pending` an, setzt Version, dann Endstatus. Die alte Reihenfolge war auf
  PostgreSQL nicht ausfuehrbar.
- `backend/tests/test_documents_read_api.py`, `test_auth_login_diagnostics.py` —
  dieselbe Korrektur, plus fehlendes `display_name`.

## Verifikationsstand

| Pruefung | Ergebnis |
|---|---|
| 29 Migrationen als lineare Kette replaybar | PASS |
| ORM == Migrationskette (bis auf 3 dokumentierte Ausnahmen) | PASS |
| `create_all` auf SQLite | PASS, 32 Tabellen |
| `tests/integration/test_schema_truth_0028_0029.py` (ohne DB) | 2 passed, 9 skipped |
| `tests/test_documents_read_api.py` | 25/26, 1 offener Streitfall (s.u.) |
| `tests/test_provisioning_service.py` | 11 passed |
| `tests/test_seed_auth_bootstrap.py`, `test_auth_login_diagnostics.py` | passed |
| Migrationen gegen echtes PostgreSQL | **OFFEN** — Skript liegt bereit |

Dokumentierte Ausnahmen im ORM-Abgleich:
1. `ck_document_chunks_source_anchor_normalized` — nutzt jsonb-Operatoren, in
   SQLite nicht darstellbar, gilt nur auf PostgreSQL.
2. `document_chunks.search_vector` — per Raw-SQL angelegt, fuer Alembic
   unsichtbar.
3. `migration_document_repairs` — bewusst ohne ORM-Modell.

## Was jetzt rot ist, und warum das die Nachricht ist

Der Abgleich hat die SQLite-Unit-Suite hart getroffen. Ueber alle Testdateien
hinweg faellt etwa ein Drittel; grob zwei Drittel dieser Ausfaelle gehen auf
**einen** neu im Modell erzwungenen Check zurueck:

    ck_documents_readable_status_requires_current_version

Das Muster ist ueberall gleich: Testfixtures legen ein Dokument mit
`import_status='chunked'` und `current_version_id=NULL` an. Genau diesen Zustand
verbietet PostgreSQL seit Migration 0010. Die Tests waren nur gruen, weil das
SQLite-Schema die Constraints nie hatte. Sie haben also gegen Zustaende geprueft,
die es in Produktion nicht gibt.

Zweithaeufigste Ursache: `ck_documents_title_not_blank` — Fixtures mit leerem
Titel.

Das restliche Drittel der Ausfaelle war **vorher schon rot** und hat mit dieser
Aenderung nichts zu tun, u.a. `ck_analysis_results_approval_metadata`
(unveraendert seit dem letzten Commit) und ein fehlendes Modul
`scripts.parent_gate_validator`.

## Offene Entscheidungen

1. **Fixture-Sanierung.** Alle betroffenen Fixtures auf die gueltige Reihenfolge
   umstellen (Dokument `pending` → Version → Endstatus). Mechanisch, aber ueber
   viele Dateien. Alternative waere, die Checks wieder aus dem Modell zu nehmen —
   dann bleibt die Unit-Suite aber weiterhin ohne Aussagewert zur Integritaet.

2. **`test_get_document_returns_409_when_document_has_no_version`.** Der Test
   baut absichtlich einen auf PostgreSQL unmoeglichen Zustand. Entweder ist der
   409-Zweig in der API toter Code, oder der Check ist zu streng. Eins von beidem
   muss weg.

3. **17 Testdateien sind vom Truth-Gate-Klassifizierer nicht erfassbar**
   (`_classify_truth_gate` in `tests/conftest.py` liefert `None`). Folge:
   `pytest tests/` bricht mit `UsageError` ab, sobald die postgres_truth-Preflight
   durchlaeuft. Die Vollsuite ist damit aktuell nicht lauffaehig.

4. **`tests/postgres_truth/test_m4e_backup_restore_truth.py`** importiert
   weiterhin `create_backup` — bekannt als EVIDENCE.md Fund 2, weiterhin offen.

5. **ENB-1 (`import_batch`/`import_batch_item`)** nicht umgesetzt. Liegt laut
   TASKS.md ausserhalb des 1.0 Scope Freeze; sinnvoll erst nach Punkt 1.

## Naechster Schritt

`verify_schema_0028_0029.ps1` gegen die echte Test-DB laufen lassen. Erst danach
ist eine Aussage ueber 0028/0029 belastbar.
