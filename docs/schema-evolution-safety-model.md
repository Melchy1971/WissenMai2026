# Schema-Evolution Safety Model

Stand: 2026-05-13

## Problem

Langlaufende Wissenssysteme degenerieren durch unsaubere Migrationen. Jede Schemaänderung ist potenziell eine Beschädigung — an Retrieval-Qualität, an historischen Citations, an Queue-Konsistenz oder an der Restore-Fähigkeit. Der Schaden ist oft nicht sofort sichtbar; er akkumuliert still als Drift.

Dieses Dokument definiert Risiko-Klassen, Schema-Evolution-Regeln und die Migrations-Governance für alle Alembic-Migrationen.

---

## 1. Prüfachsen

Jede Schemaänderung wird vor Umsetzung gegen sechs Prüfachsen bewertet:

1. Additive Migrationen: Ist die Änderung rückwärts-kompatibel, nullable/default-sicher und ohne Datenmutation?
2. Destructive Migrationen: Werden Daten, Spalten, Tabellen, Constraints oder Bedeutungen entfernt oder transformiert?
3. Reindex-Abhängigkeiten: Ändert sich `document_chunks`, `documents`, `search_vector`, `is_searchable`, Ranking oder FTS-Index?
4. Historical-Citation-Risiken: Können bestehende `chat_citations`, `chat_messages`, Snapshots oder `source_status`-Werte unlesbar werden?
5. Queue-Kompatibilität: Ändern sich `background_jobs`, Job-Typen, Status, Retry- oder Dead-Letter-Semantik?
6. Restore-Kompatibilität: Bleiben Backups, Restore in leere Ziel-DB und anschließendes `alembic upgrade head` gültig?

Die Bewertung dieser Prüfachsen bestimmt die Risiko-Klasse und die Pflichtprüfungen. Eine nicht bewertete Prüfachse ist ein Gate-Blocker.

---

## 2. Risiko-Klassen

Jede Migrationsoperation fällt in eine von vier Risiko-Klassen. Die Klasse bestimmt die Pflichtprüfungen.

### Klasse A — Sicher-Additiv

Operationen, die keine bestehenden Daten berühren und vollständig rückwärts-kompatibel sind.

| Operation | Beispiel |
|---|---|
| Neue nullable Spalte ohne Constraint | `ADD COLUMN metadata JSONB` |
| Neuer Index | `CREATE INDEX ix_documents_workspace` |
| Neue Tabelle ohne FK auf bestehende Kerntabellen | `CREATE TABLE migration_audit_log` |
| Neues CHECK-Constraint auf neuem Wert | `ADD CONSTRAINT ck_status CHECK (status IN ('a','b','c'))` |
| `server_default` auf neuer Spalte | `ADD COLUMN source_status VARCHAR DEFAULT 'active'` |

Pflichtprüfungen:
- `alembic upgrade head` gegen echte PostgreSQL
- `downgrade`-Funktion implementiert
- postgres_truth-Lauf: keine bestehenden Tests rot

Kein separater Restore-Test erforderlich.

### Klasse B — Strukturell-Erweiternd

Operationen, die bestehende Tabellen erweitern oder Constraints verschärfen, ohne Daten zu löschen oder Spalten zu entfernen.

| Operation | Beispiel |
|---|---|
| NOT NULL auf neue Spalte (mit DEFAULT) | `ADD COLUMN lifecycle_status VARCHAR NOT NULL DEFAULT 'active'` |
| FK-Änderung (bestehendes FK löschen + neues anlegen) | `chunk_id` FK auf `ON DELETE SET NULL` geändert |
| Unique Constraint auf bestehender Spalte | `ADD CONSTRAINT uq_content_hash UNIQUE (workspace_id, content_hash)` |
| Typ-Änderung kompatibel | `VARCHAR(100)` → `VARCHAR(500)` |
| `GENERATED ALWAYS AS`-Spalte | `search_vector TSVECTOR GENERATED ALWAYS AS (...)` |

Pflichtprüfungen:
- `alembic upgrade head` gegen echte PostgreSQL
- `downgrade`-Funktion implementiert und getestet
- postgres_truth-Lauf: alle betroffenen Bereiche grün
- Bestehende Datenmigration auf neuen Constraint dokumentiert
- Prüfung auf Auswirkungen für `GENERATED ALWAYS AS`-Spalten: **nie in INSERT/UPDATE aufnehmen**

### Klasse C — Destruktiv-Reversibel

Operationen, die bestehende Daten transformieren oder entfernen, aber einen dokumentierten Downgrade-Pfad haben.

| Operation | Beispiel |
|---|---|
| Spalte löschen (nach Deprecation-Phase) | `DROP COLUMN legacy_source_anchor` |
| Tabelle löschen | `DROP TABLE migration_document_repairs` |
| Daten-Backfill mit möglichem Datenverlust | Normalisierung von `source_anchor` in `0007` |
| NOT NULL ohne DEFAULT auf bestehende Spalte | erfordert Backfill-Migration davor |
| Constraint-Typ-Änderung | FK zu `ON DELETE CASCADE` |

Pflichtprüfungen:
- `alembic upgrade head` gegen echte PostgreSQL
- `downgrade`-Funktion implementiert **und lokal gegen einen Snapshot getestet**
- Restore-Test: Backup vor Migration erstellen, nach Migration Restore verifizieren
- postgres_truth-Lauf: alle 7 Impact-Bereiche aus Architecture Change Governance geprüft
- Historical-Citation-Risiko explizit bewertet (Abschnitt 5)
- Datenverlust-Inventar: was geht verloren und warum ist das akzeptabel?
- `irreversible: false` in Migrations-Header dokumentiert

### Klasse D — Destruktiv-Irreversibel

Operationen, die keine verlustfreie Rückkehr ermöglichen. Die höchste Risikostufe.

| Operation | Beispiel |
|---|---|
| `DROP TABLE` mit Fremdschlüsseln | Löschen einer Kerntabelle |
| `DROP COLUMN` mit Daten ohne Backup | Löschen von `normalized_markdown` |
| Typ-Änderung mit Datenverlust | `JSONB` → `VARCHAR` mit Truncation |
| Entfernung eines Unique Constraints mit bestehenden Duplikaten | |
| Migration, die `content_hash`-Eindeutigkeit aufhebt | |
| Änderung des `search_vector GENERATED ALWAYS AS`-Ausdrucks | betrifft FTS-Index und Retrieval |

Pflichtprüfungen (alle Pflichten aus Klasse C, plus):
- `irreversible: true` im Migrations-Header
- Explizite schriftliche Freigabe bevor die Migration committed wird
- Vollständiger Restore-Test: Backup vor Migration, Migration durchführen, Restore in leere DB, Verifikation aller INV-001 bis INV-020 aus `docs/data-model-invariants.md`
- postgres_truth-Lauf nach Migration: **alle Tests grün, keine Skips**
- Datenverlust-Inventar: vollständig, versioniert, als Kommentar in der Migrationsdatei

---

## 3. Schema-Evolution-Regeln

### Regel SE-01: Namens-Präfix-Konvention

Jede Migrationsdatei **muss** dem Muster `YYYYMMDD_NNNN_beschreibung.py` folgen.

```
20260512_0015_add_entropy_baseline_table.py
```

- `YYYYMMDD`: Datum der Migration
- `NNNN`: vierstellige Sequenznummer, innerhalb eines Tages eindeutig
- `beschreibung`: kurze snake_case-Beschreibung der Änderung

Verstöße gegen diese Konvention sind ein Gate-Blocker.

### Regel SE-02: Kein implizites alembic head

Der alembic-Head ist die verbindliche Wahrheitsquelle für den Datenbankstand.

- `alembic upgrade head` muss vor jedem postgres_truth-Lauf erfolgreich sein
- Migration-Fehler sind `FAIL`, nicht Skip
- `alembic heads` darf genau eine Revision zurückgeben (kein Split-Head)
- `reports/postgres_truth_report.json` enthält `alembic_heads`; dieser Wert muss mit `alembic heads` übereinstimmen

### Regel SE-03: GENERATED ALWAYS AS ist schreibgeschützt

Die Spalte `document_chunks.search_vector` ist `GENERATED ALWAYS AS` definiert.

- Diese Spalte darf **niemals** in einem `INSERT` oder `UPDATE` aufgelistet werden
- Kein ORM-Mapping darf `search_vector` als beschreibbares Attribut deklarieren
- Jede Migration, die `document_chunks` verändert, muss prüfen, ob der Generator-Ausdruck noch korrekt ist
- Eine Änderung des Generator-Ausdrucks ist Klasse D

### Regel SE-04: Downgrade-Funktion ist Pflicht

Jede Migration benötigt eine implementierte `downgrade()`-Funktion.

```python
def downgrade() -> None:
    # IRREVERSIBLE: Datenverlust nicht rückgängig zu machen
    # Grund: ...
    pass  # nur erlaubt bei Klasse D mit expliziter Markierung
```

Ein leeres `pass` ohne Kommentar ist verboten. Wenn downgrade wirklich nicht möglich ist: `pass` mit Begründung und `IRREVERSIBLE`-Markierung.

Jede Migration muss im Header bewerten, ob der Downgrade verlustfrei, verlustbehaftet oder unmöglich ist. Diese Bewertung entscheidet mit über Klasse A-D.

### Regel SE-05: Dialect-Awareness für PostgreSQL-spezifische Features

Migrationen, die PostgreSQL-spezifische Features nutzen (`JSONB`, `TSVECTOR`, `pg_try_advisory_xact_lock`, `GIN`-Index), müssen dialect-aware sein:

```python
bind = op.get_bind()
if bind.dialect.name == "postgresql":
    # PostgreSQL-spezifische Operation
```

Kein PostgreSQL-spezifisches Feature ohne dialect-Guard. Andernfalls schlägt `alembic upgrade head` gegen SQLite-Testumgebungen fehl.

### Regel SE-06: Backfill vor Constraint

Wenn ein neues NOT NULL-Constraint oder ein Unique Constraint auf eine bestehende Spalte gesetzt wird, muss der Backfill in derselben Migration **vor** dem Constraint erfolgen:

```python
def upgrade():
    # 1. Backfill
    op.execute("UPDATE documents SET lifecycle_status = 'active' WHERE lifecycle_status IS NULL")
    # 2. Constraint
    op.alter_column("documents", "lifecycle_status", nullable=False)
```

Constraint vor Backfill führt zu `IntegrityError` auf bestehenden Daten — das ist ein Test-FAIL und ein Produktions-FAIL.

### Regel SE-07: Repair-Migrationen sind Klasse C, nicht Klasse A

Migrationen, die bestehende Daten transformieren (auch reparieren), sind mindestens Klasse C. Beispiel: `0010_repair_legacy_document_states.py`.

Repair-Migrationen **müssen**:
- einen Audit-Log-Eintrag für jede modifizierte Zeile erzeugen (wie `migration_document_repairs`)
- in `downgrade()` dokumentieren, ob der Reparaturzustand rückgängig gemacht werden kann

### Regel SE-08: FK-Änderungen sind explizit

Eine FK-Änderung (auch `ON DELETE SET NULL` statt `ON DELETE RESTRICT`) muss im Migration-Kommentar begründet werden. Beispiel aus `20260506_0013`:

```python
# chunk_id: FK wird zu ON DELETE SET NULL geändert,
# damit historische Citations nach Chunk-Löschung erhalten bleiben.
```

Implizite FK-Änderungen ohne Kommentar sind verboten.

### Regel SE-09: Destructive Migrationen nur mit Restore-Test

Jede Klasse-C- oder Klasse-D-Migration braucht vor Merge einen Restore-Test. Der Test muss mindestens belegen:

- Backup vor Migration erstellt und verifiziert
- Migration gegen echte PostgreSQL-DB ausgeführt
- Restore in leere Ziel-DB erfolgreich
- `alembic upgrade head` nach Restore erfolgreich
- `postgres_truth` oder definierter Truth-Smoke nach Restore grün

Eine destructive Migration ohne Restore-Test ist verboten.

### Regel SE-10: Irreversible Migrationen kennzeichnen

Jede irreversible Migration ist Klasse D und muss im Migrations-Header `IRREVERSIBLE: true` tragen. Zusätzlich braucht sie ein Datenverlust-Inventar und eine explizite Begründung, warum der Verlust akzeptiert wird.

### Regel SE-11: Alembic Head ist Truth-Gegenstand

Der aktuelle Alembic-Head ist nicht nur ein technischer Stand, sondern ein Truth-Artefakt. Jeder postgres_truth-Lauf muss `alembic_heads` im Report ausweisen. Der Wert muss mit `alembic heads` übereinstimmen; Split-Heads oder fehlende Heads blockieren Merge und Freigabe.

---

## 4. Additive Migrationen

Additive Migrationen (Klasse A und B) sind der bevorzugte Pfad. Sie sind rückwärts-kompatibel und minimieren das Risiko für alle 6 betroffenen Systembereiche.

**Muster für Klasse A:**

```python
def upgrade() -> None:
    op.add_column("documents", sa.Column("entropy_baseline", sa.JSONB(), nullable=True))

def downgrade() -> None:
    op.drop_column("documents", "entropy_baseline")
```

**Muster für Klasse B (NOT NULL mit DEFAULT, dann Constraint verschärfen):**

```python
def upgrade() -> None:
    # Schritt 1: nullable mit default
    op.add_column("documents", sa.Column(
        "lifecycle_status", sa.String(32), nullable=True, server_default="active"
    ))
    # Schritt 2: Backfill
    op.execute("UPDATE documents SET lifecycle_status = 'active' WHERE lifecycle_status IS NULL")
    # Schritt 3: NOT NULL setzen
    op.alter_column("documents", "lifecycle_status", nullable=False)

def downgrade() -> None:
    op.drop_column("documents", "lifecycle_status")
```

**Inkompatibles additives Antipattern** (verboten):

```python
# VERBOTEN: NOT NULL ohne Backfill auf bestehende Zeilen
op.add_column("documents", sa.Column("status", sa.String(), nullable=False))
```

---

## 5. Destructive Migrationen und Historical Citation Risiken

### 5.1 Generelle Regeln für destructive Migrationen

Destructive Migrationen (Klasse C/D) sind nur zulässig wenn:

1. Ein Backup der Datenbank vor der Migration existiert und verifiziert ist
2. Ein Restore-Test erfolgreich durchgelaufen ist (Restore in leere DB, Verifikation)
3. Das Datenverlust-Inventar vollständig ist
4. postgres_truth nach der Migration grün ist

### 5.2 Historical Citation Risiken

Citations sind das langlebigste Datenobjekt im System. Einmal gespeicherte Citations müssen nach jedem Schema-Upgrade noch lesbar und auswertbar sein. Folgende Operationen an Citations-nahen Tabellen sind Klasse D:

| Operation | Risiko |
|---|---|
| DROP COLUMN auf `chat_citations` | Historische Citations verlieren Felder permanent |
| Änderung des `chunk_id`-FK-Verhaltens | Orphan-Citations können entstehen oder verschwinden |
| Umbenennung von `source_status`-Werten | Citation-Longevity-Tests schlagen fehl |
| DROP TABLE `chat_messages` oder `chat_sessions` | Citations sind nicht mehr rekonstruierbar |
| Änderung des `quote_preview`-Datentyps | Snapshot-Inhalte könnten abgeschnitten werden |

Für jede Operation an `chat_citations`, `chat_messages`, `chat_sessions`:

1. `test_citation_longevity_truth.py` muss nach der Migration grün sein
2. Bestehende Citation-Snapshots dürfen nicht in einen ungültigen Zustand geraten
3. `source_status`-Werte (`active`, `archived`, `deleted`, `missing`) sind verbindlich; neue Werte erfordern einen Migrations-Backfill

### 5.3 Irreversible Migrationen kennzeichnen

Migrations-Header für irreversible Operationen:

```python
"""drop legacy source anchor column

IRREVERSIBLE: Diese Migration löscht document_chunks.legacy_source_anchor.
Datenverlust: alle legacy_source_anchor-Werte gehen verloren.
Akzeptiert, weil: Spalte seit 20260507 deprecated, kein aktiver Code-Pfad liest sie.
Backup-Pflicht: Backup vor Ausführung erforderlich, Restore-Test erfolgreich am YYYY-MM-DD.

Revision ID: 20260512_0016
"""

def downgrade() -> None:
    # IRREVERSIBLE: Daten sind nach DROP COLUMN nicht wiederherstellbar.
    # Backup vor Migration ist Voraussetzung.
    pass
```

---

## 6. Reindex-Abhängigkeiten

Schemaänderungen an `document_chunks` oder `documents` können den FTS-Index invalidieren.

### 6.1 Operationen, die REINDEX erfordern

| Operation | Warum |
|---|---|
| Änderung des `GENERATED ALWAYS AS`-Ausdrucks für `search_vector` | Index basiert auf dem Ausdruck |
| DROP/ADD GIN-Index auf `search_vector` | FTS-Lookups schlagen fehl |
| Änderung der Kollatierung von `text`-Spalten | Ranking-Ergebnisse ändern sich |
| UPDATE auf `document_chunks.text` ohne Trigger-Update | `search_vector` wird nicht automatisch aktualisiert — ist aber GENERATED, also kein Problem |
| Änderung von `is_searchable` durch eine Migration | Direkte Auswirkung auf Retrieval Coverage |

### 6.2 REINDEX-Pflicht nach Klasse-C/D-Migrationen

Wenn eine Klasse-C- oder Klasse-D-Migration Chunks betrifft:

```sql
-- Nach der Migration ausführen:
UPDATE document_chunks SET is_searchable = FALSE
WHERE document_id IN (
    SELECT id FROM documents WHERE lifecycle_status IN ('archived', 'deleted')
);
```

Ohne diesen Schritt entstehen stale-index-Einträge — ein Entropy-Risiko.

### 6.3 `is_searchable` ist keine freie Variable

`is_searchable` darf nur über folgende definierte Pfade gesetzt werden:

- `SearchIndexRebuildService.rebuild_for_document()` — normaler Reindex
- `ReindexGovernanceService.run_governed_reindex()` — governed Reindex
- Eine explizite Repair-Migration mit Audit-Log

Jede Migration, die `is_searchable` direkt setzt, ist Klasse C und muss `test_reindex_governance_truth.py` danach grün halten.

---

## 7. Queue-Kompatibilität

### 7.1 Job-Typen sind Teil des Schemas

Die Tabelle `background_jobs` hat ein `job_type`-Feld. Neue Job-Typen, umbenannte Job-Typen und gelöschte Job-Typen sind Schemaänderungen.

| Änderung | Klasse | Risiko |
|---|---|---|
| Neuer Job-Typ | B | Queue-Aging-Detection erkennt unbekannten Typ |
| Umbenennung Job-Typ (laufende Jobs) | D | Laufende Jobs mit altem Typ werden nie abgearbeitet |
| Umbenennung Job-Typ (nach Drain) | C | Kein Verlust, aber Downgrade nicht möglich |
| Neuer Job-Status | B | Dead-Letter-Pfad muss den Status kennen |
| Entfernung eines Job-Status | C/D | Bestehende Jobs in diesem Status werden Zombies |

### 7.2 Migrations-Pflicht bei Job-Typ-Änderungen

Wenn ein Job-Typ umbenannt wird:

```python
def upgrade() -> None:
    # Vor Umbenennung: sicherstellen, dass keine Jobs mit altem Typ offen sind
    op.execute("""
        UPDATE background_jobs
        SET job_type = 'document_import_v2'
        WHERE job_type = 'document_import' AND status = 'queued'
    """)
    # Laufende Jobs dürfen nicht umbenannt werden
```

### 7.3 Dead-Letter-Invariante

Jeder neue Job-Typ muss einen Dead-Letter-Pfad haben. Eine Migration, die einen neuen Job-Typ einführt, ohne den Dead-Letter-Schwellwert zu definieren, erzeugt stille Starvation.

Nach jeder Queue-Schema-Änderung: `test_queue_aging_truth.py` muss grün sein.

---

## 8. Restore-Kompatibilität

### 8.1 Backup-Schema-Versionsträger

Das Backup-Manifest enthält `alembic_heads`. Wenn nach einem Restore ein `alembic upgrade head` notwendig ist, muss der Upgrade-Pfad lückenlos sein.

Invariante: Jede Migrationskette vom ältesten unterstützten Backup bis zum aktuellen Head muss ohne Fehler upgraden können.

### 8.2 Klasse-D-Migrationen brechen ältere Backups

Eine destruktive-irreversible Migration bedeutet: Backups, die vor dieser Migration erstellt wurden, sind **nicht mehr direkt restorbar** auf den aktuellen Stand. Sie erfordern einen Upgrade-Lauf nach dem Restore.

Pflicht vor jeder Klasse-D-Migration:
- Aktuelles Backup erstellen
- Restore in leere DB testen
- Upgrade auf neuen Head nach Restore testen
- Verifikation: alle postgres_truth-Tests grün nach Restore + Upgrade

### 8.3 Restore-Verifikations-Checkliste

Nach jeder Klasse-C- oder Klasse-D-Migration:

```
[ ] Backup vor Migration erstellt
[ ] alembic upgrade head erfolgreich
[ ] Restore in leere Ziel-DB: alembic upgrade head erfolgreich
[ ] INV-001 bis INV-020 (data-model-invariants.md) nach Restore gültig
[ ] postgres_truth: alle Tests grün nach Restore
[ ] citation_longevity: historische Citations nach Restore lesbar
[ ] queue_aging: keine Zombie-Jobs nach Restore
[ ] BackupRestoreService.verify_backup() gibt OK zurück
```

---

## 9. Downgrade-Pfade bewerten

Downgrade-Fähigkeit ist kein Bonus — sie ist Pflicht. Jede Migration muss eine explizite Downgrade-Bewertung haben.

### Bewertungsmatrix

| Migration | Downgrade möglich? | Datenverlust bei Downgrade? | Klasse |
|---|---|---|---|
| Neue nullable Spalte | ja | nein | A |
| Neuer Index | ja | nein | A |
| NOT NULL auf neue Spalte | ja (DROP COLUMN) | nein | B |
| Unique Constraint | ja (DROP CONSTRAINT) | nein | B |
| Spalte löschen | nein (ohne Backup) | ja | C/D |
| Tabelle löschen | nein | ja | D |
| Typ-Änderung mit Truncation | nein | ja | D |
| Backfill ohne Originalwerte | nein | ja | C/D |

### Downgrade-Test-Anforderungen

Für Klasse B: `downgrade()`-Funktion muss implementiert sein, lokal testbar.

Für Klasse C: `downgrade()`-Funktion implementiert **und** lokal gegen einen Snapshot getestet. Ergebnis dokumentiert.

Für Klasse D: `downgrade()` darf `pass` enthalten, aber **muss** den Kommentar-Block mit Datenverlust-Inventar enthalten. Ein postgres_truth-Lauf nach Downgrade ist nicht erforderlich (weil Downgrade nicht erwünscht ist), aber ein Backup vor Migration ist absolut Pflicht.

---

## 10. Alembic Head Truth-Validierung

### 10.1 Split-Head-Verbot

`alembic heads` darf genau **eine** Revision zurückgeben. Ein Split-Head ist ein Gate-Blocker.

Ursachen für Split-Heads:
- Zwei parallele Migrations-Branches ohne gemeinsamen `down_revision`
- Fehlende Merge-Migration nach paralleler Entwicklung

Behebung: eine Merge-Migration erstellen:
```bash
alembic merge -m "merge_parallel_heads" <rev1> <rev2>
```

### 10.2 postgres_truth validiert alembic head

Das Feld `alembic_heads` in `reports/postgres_truth_report.json` ist Pflicht. Der M4-Gate-Validator prüft, dass dieser Wert nicht leer ist.

Jeder postgres_truth-Lauf muss mit einem konsistenten alembic-Head starten. Ein Lauf mit unvollständiger Migrationskette ist ein FAIL.

### 10.3 Head-Validierungs-Workflow

Vor jedem postgres_truth-Lauf:

```powershell
# 1. Alembic-Stand prüfen
cd backend
alembic heads         # muss genau eine Revision zeigen
alembic current       # muss = alembic heads sein

# 2. Falls nicht aktuell: upgrade
alembic upgrade head

# 3. postgres_truth ausführen
cd ..
.\scripts\run-postgres-truth.ps1

# 4. Head im Report prüfen
# reports/postgres_truth_report.json: alembic_heads = ["YYYYMMDD_NNNN"]
```

---

## 11. Migrations-Governance — Kurzreferenz

### Pflicht-Header für jede Migration

```python
"""<kurze Beschreibung der Änderung>

KLASSE: A | B | C | D
IRREVERSIBLE: true | false
DATENVERLUST: keine | <Beschreibung was verloren geht>
RESTORE-TEST: erforderlich | nicht erforderlich | abgeschlossen am YYYY-MM-DD
BETROFFENE BEREICHE: postgres_truth | recovery | drift | retrieval | queue | citations | backup

Revision ID: YYYYMMDD_NNNN
"""
```

### Pflicht-Checkliste vor Merge

```
[ ] Klasse bestimmt (A/B/C/D)
[ ] KLASSE und IRREVERSIBLE im Header dokumentiert
[ ] downgrade() implementiert (oder mit IRREVERSIBLE-Kommentar)
[ ] dialect-Guard für PostgreSQL-spezifische Features
[ ] Backfill vor Constraint (Klasse B/C)
[ ] GENERATED ALWAYS AS nicht in INSERT/UPDATE
[ ] Für Klasse C/D: Backup erstellt, Restore-Test bestanden
[ ] alembic upgrade head erfolgreich gegen echte PostgreSQL
[ ] alembic heads = 1 Revision (kein Split-Head)
[ ] postgres_truth-Lauf: passed=N, failed=0, skipped=0
[ ] Betroffene Truth-Tests nach Migration grün (citation_longevity, queue_aging, reindex_governance)
[ ] Datenverlust-Inventar vollständig (Klasse C/D)
```

### Entscheidungsbaum

```
Neue Spalte nullable?
  → Klasse A

Neue Spalte NOT NULL mit DEFAULT?
  → Klasse B: Backfill-Pflicht

Spalte ändern (Typ, Nullable, Constraint)?
  → Typ kompatibler?  ja → Klasse B
                      nein → Klasse C oder D

Spalte oder Tabelle löschen?
  → Downgrade möglich?  ja → Klasse C
                        nein → Klasse D: IRREVERSIBLE, Backup-Pflicht

Daten transformieren (Backfill, Normalisierung)?
  → Originalwerte erhalten?  ja → Klasse C
                             nein → Klasse D

GENERATED ALWAYS AS ändern?
  → Klasse D: Retrieval-Impact hoch
```

---

## 12. Beziehung zu anderen Dokumenten

| Dokument | Verhältnis |
|---|---|
| `docs/data-model-invariants.md` | Invarianten INV-001 bis INV-020, die jede Migration erhalten muss |
| `docs/architecture-change-governance.md` | Übergeordneter Change-Control-Prozess; dieses Dokument konkretisiert Schema-Aspekte |
| `docs/operational-truth-governance.md` | Truth-Quellen; `alembic_heads` ist Pflichtfeld im Truth-Report |
| `backend/migrations/versions/` | Ground Truth für alle Migrationen |
| `scripts/validate_m4_truth_gate.py` | Validator; prüft `alembic_heads` im Report |
