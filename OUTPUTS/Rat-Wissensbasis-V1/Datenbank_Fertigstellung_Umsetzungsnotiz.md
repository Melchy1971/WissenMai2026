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

## Nachtrag 3 — erster Live-Lauf: 0028 hatte die falsche Drop-Reihenfolge

Beim ersten Lauf gegen echtes PostgreSQL (lokale Dev-DB, Container `testdb`)
scheiterte 0028:

```
psycopg.errors.DependentObjectsStillExist: cannot drop table analysis_groups
DETAIL: constraint fk_analysis_results_group_id on table analysis_results_legacy
        depends on table analysis_groups
```

Ursache: `analysis_results_legacy` haengt per FK an `analysis_groups`. In der
ersten Fassung stand `analysis_groups` an zweiter Stelle der Drop-Liste, also vor
seinem eigenen Abhaengigen. Korrigierte Reihenfolge:

    analysis_group_documents
    analysis_result_sources_legacy
    analysis_results_legacy
    analysis_groups

Der Downgrade legt die Tabellen jetzt in umgekehrter Reihenfolge an und stellt
`fk_analysis_results_group_id` wieder her, was in der ersten Fassung fehlte.

**Was das ueber die Absicherung sagt:** Der DB-freie Replay-Test
(`test_orm_matches_migration_chain`) konnte das nicht finden. Er zeichnet
Operationen in ein Schemamodell und wertet FK-Abhaengigkeiten beim Drop nicht
aus — ein statisches Replay kann DDL-Reihenfolgefehler prinzipiell nicht sehen.
Nur eine echte Datenbank findet so etwas. Genau dafuer gibt es
`verify_schema_0028_0029.ps1`; der Fehler ist der Beleg, dass der Live-Lauf
nicht optional ist.

Transaktionales DDL hat den fehlgeschlagenen Schritt zurueckgerollt; die DB blieb
auf `20260724_0027` stehen. Kein Datenverlust, kein halber Zustand.

## Nachtrag 2 — Inventar der toten Regeln (Stand Ende der Sitzung)

Die Fixture-Sanierung hat nicht vier, sondern **neun** Anwendungsregeln
freigelegt, die Zustaende pruefen, die das Schema bereits ausschliesst. Entfernt
sind die ersten sechs; drei stehen noch aus.

### Entfernt

| Regel | Blockiert durch |
|---|---|
| `DuplicateDetector` (kompletter Detektor, Datei geloescht) | `uq_documents_workspace_content_hash` |
| `MetadataQualityDetector` MQ-1 (leerer Titel) | `ck_documents_title_not_blank` |
| `MetadataDriftDetector._check_title` (leerer Titel, 2. Kopie) | `ck_documents_title_not_blank` |
| `MissingMetadataDetector` (leerer Titel, 3. Kopie) | `ck_documents_title_not_blank` |
| `InvalidLifecycleDetector` | `ck_documents_lifecycle_status_allowed` — die erlaubte Menge des Detektors war sogar weiter als die der DB |
| `read_service.get_document_detail`, erster 409-Zweig | `ck_documents_readable_status_requires_current_version` |

Zusaetzlich entfernt: `OrphanChunkDetector` und `EmptyChunkDetector` — beide nie
ueber das Skelett hinaus, `detect()` lieferte immer `[]`. Damit laufen im
Data-Quality-Runner **vier statt acht** Detektoren.

Drei Kopien derselben Titelpruefung in drei Subsystemen, keine davon
funktionsfaehig — das ist der Kern des Befunds.

### Noch offen

| Regel | Blockiert durch |
|---|---|
| `DocumentDriftDetector` Check 1, Teil "hat current_version_id" | `ck_documents_readable_status_requires_current_version` (der Teil "hat Chunks" bleibt gueltig) |
| `DocumentDriftDetector` Check 2 "Version aufloesbar" | FK `fk_documents_current_version_id_document_versions` |
| Chunk-Graphen in `test_search_index_service.py` | `uq_document_chunks_version_chunk_index` und `fk_document_chunks_document_version_pair` |

### Konsequenz fuer den Quality Score

Der Score wurde bisher aus acht Detektoren gebildet, von denen fuenf strukturell
nie ausschlagen konnten. Er war damit nicht falsch berechnet, aber strukturell
zu optimistisch: fuenf Kategorien meldeten per Konstruktion null Befunde.
`reports/current/product_maturity_v2.json` und der M5a-Gate-Stand sollten nach
dieser Aenderung neu bewertet werden.

### Governance-Auswirkung, die entschieden werden muss

`duplicate_detector_gate` ist in `docs/gate_hierarchy.json` ein
**mandatory_child von M5a**, mit `reports/current/m5a_duplicate_detector_gate.json`
als Nachweis. Mit dem Detektor faellt auch das Gate. Ich habe die
Gate-Hierarchie **nicht** angefasst — das ist eine Governance-Entscheidung, kein
Refactoring.

## Nachtrag 1: die Fixture-Sanierung hat toten Code freigelegt

Beim Umstellen der Fixtures auf gueltige Dokumentzustaende zeigt sich, dass die
Sache groesser ist als eine Testreparatur. **Vier Anwendungsregeln pruefen
Zustaende, die das Schema bereits verbietet.** Sie koennen auf PostgreSQL nie
zuschlagen; ihre Tests waren nur gruen, weil das SQLite-Schema die Constraints
nicht hatte.

| Regel | Blockiert durch | Status |
|---|---|---|
| `DuplicateDetector` (kompletter Detektor) | `uq_documents_workspace_content_hash` — unbedingtes UNIQUE auf (workspace_id, content_hash) | unerreichbar |
| `MetadataQualityDetector` Regel MQ-1 (leerer Titel) | `ck_documents_title_not_blank` | unerreichbar |
| `read_service.get_document_detail`, erster 409-Zweig ("Document exists without a latest version") | `ck_documents_readable_status_requires_current_version` | unerreichbar |
| Chunk-Graphen in `test_search_index_service.py` | `uq_document_chunks_version_chunk_index` + `fk_document_chunks_document_version_pair` | unerreichbar |

Der `DuplicateDetector` ist der deutlichste Fall: er sucht innerhalb eines
Workspace nach mehreren aktiven Dokumenten mit gleichem `content_hash`. Genau
das schliesst das UNIQUE aus Migration 0005 aus. Er filtert zusaetzlich auf
`content_hash IS NOT NULL` und `trim(content_hash) <> ''` — beides ebenfalls
durch `NOT NULL` und `ck_documents_content_hash_not_blank` ausgeschlossen. Der
Detektor liefert auf der echten DB immer eine leere Liste.
22 der 23 Tests in `test_duplicate_detector.py` koennen den Ausgangszustand gar
nicht mehr herstellen.

Der zweite 409-Zweig in `read_service` ("chunked, aber Version ohne Chunks")
bleibt dagegen erreichbar und ist echt.

Das ist die eigentliche Antwort auf "Datenbank zu Ende entwickeln": Schema und
Data-Quality-Layer sind unabhaengig voneinander gewachsen und ueberlappen. Die
SQLite-Testbasis hat die Ueberlappung verdeckt.

### Fixtures bereits saniert

| Datei | Ergebnis |
|---|---|
| `tests/conftest.py` (`document_fixture`) | gruen |
| `tests/test_documents_read_api.py` | 25/26 |
| `tests/test_orphan_detector.py` | gruen |
| `tests/test_lifecycle_integrity_detector.py` | gruen |
| `tests/test_metadata_quality_detector.py` | 30/41, Rest haengt an MQ-1 |
| `tests/test_search_index_service.py` | 4/6, Rest haengt am Chunk-Graphen |
| `tests/test_auth_login_diagnostics.py` | gruen |

Muster: `_doc()` legt mit `import_status='pending'` an, `_version()` zieht den
Endstatus nach, sobald die Version existiert. Das ist derselbe Weg, den
`import_persistence_service.py` produktiv geht (`update documents set
current_version_id = %s, import_status = %s`).

Noch offen: 11 weitere Dateien mit demselben Muster. Ich habe sie bewusst nicht
angefasst, solange die Entscheidung zu den toten Regeln aussteht — bei
`test_duplicate_detector.py` waere jede Fixture-Reparatur Arbeit an einem
Detektor, der vielleicht ganz verschwindet.

## Offene Entscheidungen

1. **Fixture-Sanierung.** Alle betroffenen Fixtures auf die gueltige Reihenfolge
   umstellen (Dokument `pending` → Version → Endstatus). Mechanisch, aber ueber
   viele Dateien. Alternative waere, die Checks wieder aus dem Modell zu nehmen —
   dann bleibt die Unit-Suite aber weiterhin ohne Aussagewert zur Integritaet.

2. **Tote Regeln: entfernen oder Constraints lockern?** Betrifft
   `DuplicateDetector`, `MetadataQualityDetector` MQ-1 und den ersten
   409-Zweig in `read_service`. Entweder die Regeln fliegen raus (dann sinkt die
   Data-Quality-Abdeckung nominal, faktisch aendert sich nichts, weil sie nie
   ausgeloest haben), oder die Constraints muessen weg (dann werden genau die
   Datenfehler wieder moeglich, die die Regeln melden sollten). Meine Einschaetzung:
   Constraints behalten, Regeln entfernen — eine DB-Garantie ist staerker als
   eine nachtraegliche Meldung. Aber das ist eine PO-Entscheidung, keine
   technische.

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
