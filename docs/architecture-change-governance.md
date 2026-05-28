# Architecture Change Governance

Stand: 2026-05-13

## Ziel

Jede Architekturänderung wird bewertet, bevor sie das System berührt. Keine Änderung darf die bestehende Systemstabilität untergraben — weder absichtlich noch implizit durch ungeplante Seiteneffekte.

Dieses Dokument definiert verbindliche Governance-Regeln, Pflichtprüfungen und den Change-Control-Prozess für alle Architekturänderungen an der Wissensbasis.

---

## 1. Geltungsbereich

Governance-pflichtig sind alle Änderungen, die mindestens einen der folgenden Bereiche berühren:

| Bereich | Beispiele |
|---|---|
| Datenbankschema | neue Tabellen, Spalten, Constraints, Index-Änderungen, Migration |
| Service-Contracts | Änderungen an Service-Signaturen, Dependency-Injection-Ketten |
| Lifecycle-Logik | Statusübergänge, Soft-Delete-Regeln, Archivierungsverhalten |
| Queue-Semantik | Job-Typen, Status-Übergänge, Retry-Logik, Dead-Letter-Verhalten |
| Reindex-Logik | `is_searchable`-Regeln, Chunk-Reparatur, Advisory-Lock-Scopes |
| Citation-Pfade | Snapshot-Erstellung, `source_status`-Lookup, Orphan-Behandlung |
| Backup/Restore-Pfade | Backup-Manifest, Restore-Orchestrierung, Validierungslogik |
| Auth/Workspace-Isolation | Session-Modell, Membership-Checks, Workspace-Binding |
| Admin-API-Contracts | neue oder geänderte Admin-Endpunkte |

Explizit nicht governance-pflichtig (aber trotzdem testpflichtig):

- Reine Textänderungen in Fehlermeldungen ohne Code-Änderung
- Kommentare und Dokumentation
- Test-only-Änderungen ohne Produktionscode-Einfluss

---

## 2. Verbotene Muster

Die folgenden Muster sind ohne vollständigen Change-Control-Prozess verboten:

| Verbotenes Muster | Begründung |
|---|---|
| "kleine Änderung ohne Risikoanalyse" | Jede Schemaänderung kann den gesamten postgres_truth-Stack brechen |
| Ungetestete Schemaänderungen | Jede Migration muss vor dem Merge gegen eine echte PostgreSQL-Instanz laufen |
| Implizite Lifecycle-Änderungen | Statusübergänge müssen explizit sein; kein implizites `deleted_at`-Setzen außerhalb des Lifecycle-Service |
| Schemaänderung ohne Migrations-Präfix-Konvention | Migrationen müssen `YYYYMMDD_NNNN_` Präfix haben |
| Advisory-Lock-Scope-Erweiterung ohne Safety-Gate-Prüfung | Neue Scopes können bestehende Locks konkurrieren |
| Änderung an `GENERATED ALWAYS AS`-Spalten | `search_vector` darf nie in INSERT/UPDATE enthalten sein |
| Einführung neuer Queue-Status ohne Dead-Letter-Pfad | Neue Status können zu stillen Starvation-Zuständen führen |
| Änderung des Citation-Snapshot-Modells ohne Longevity-Test-Update | Historische Citations müssen nach der Änderung noch lesbar sein |

---

## 3. Pflichtartefakte

Jede governance-pflichtige Architekturänderung muss vor Implementierungsbeginn vier Artefakte besitzen:

1. Impact Assessment: alle 7 Stabilitätsbereiche bewertet
2. Risk Matrix: Risiken, Schwere, Wahrscheinlichkeit, Mitigation und Gate-Wirkung
3. Truth-Test-Plan: konkrete Tests, Befehle, erwartete Reports und Gate-Bedingungen
4. Rollback-Plan: Trigger, Schritte, Datenverlustbewertung und Verifikation

Keines dieser Artefakte ist optional. Eine Änderung ohne vollständige Artefakte gilt als nicht freigabefähig, auch wenn der Code klein wirkt oder nur einen einzelnen Service betrifft.

---

## 4. Impact Assessment (Pflichtartefakt)

Für jede governance-pflichtige Änderung ist ein Impact Assessment verpflichtend. Es beantwortet alle folgenden 7 Fragen mit je einer expliziten Einschätzung (`keine`, `gering`, `mittel`, `hoch`, `blockierend`) und einer kurzen Begründung.

Eine Teilbewertung ist verboten. Auch wenn ein Bereich scheinbar nicht betroffen ist, muss `keine` mit Begründung dokumentiert werden.

### 4.1 Auswirkungen auf postgres_truth

- Werden bestehende Truth-Tests durch die Änderung ungültig?
- Muss eine neue Fixture oder ein neuer Marker eingeführt werden?
- Welche `test_*.py`-Dateien unter `backend/tests/postgres_truth/` sind betroffen?
- Müssen neue Tests hinzugefügt werden, bevor die Änderung gemergt werden darf?

Entscheidungsregel: Eine Änderung, die bestehende postgres_truth-Tests red macht, ist ein Gate-Blocker. Sie darf nicht gemergt werden, bevor alle betroffenen Tests wieder grün sind.

### 4.2 Auswirkungen auf Recovery

- Verändert die Änderung das Verhalten nach Absturz (Crash-Recovery-Matrix)?
- Sind `crash_import_worker.py` oder `crash_reindex_worker.py` betroffen?
- Bleibt die Invariante „nach Advisory-Lock-Ablauf ist der Zustand konsistent" erhalten?
- Welche Recovery-Pfade müssen nach der Änderung neu getestet werden?

### 4.3 Auswirkungen auf Drift

- Verändert die Änderung die Definition von „stale index" (`is_searchable` vs. `lifecycle_status`)?
- Verändert sie, was als „orphan chunk" gilt?
- Beeinflusst sie die `EntropyMetrics`-Berechnung in `entropy_helpers.py`?
- Müssen `STALE_RATE_MAX`, `ORPHAN_RATE_MAX` oder `RETRIEVAL_COVERAGE_MIN` angepasst werden?

### 4.4 Auswirkungen auf Retrieval Quality

- Verändert die Änderung, welche Chunks searchable sind?
- Verändert sie den `ts_rank`-Pfad oder den FTS-Index?
- Bleibt `RETRIEVAL_COVERAGE_MIN = 0.85` nach der Änderung erreichbar?
- Müssen Retrieval-Regressionstests aktualisiert werden?

### 4.5 Auswirkungen auf Queue-Konsistenz

- Werden neue Job-Typen eingeführt oder bestehende umbenannt?
- Ändert sich die Retry-Logik oder der Dead-Letter-Schwellwert?
- Bleibt die Queue-Aging-Erkennung korrekt für alle neuen Job-Typen?
- Sind `inject_retryable_jobs` oder `inject_dead_letter_jobs` in `entropy_helpers.py` betroffen?

### 4.6 Auswirkungen auf Historical Citations

- Ändert sich das Schema von `chat_citations` oder `chat_messages`?
- Bleibt der `source_status`-Live-Lookup (`active|archived|deleted|missing`) korrekt?
- Werden bestehende Citation-Snapshots durch die Änderung ungültig?
- Müssen `test_citation_longevity_truth.py`-Tests angepasst werden?

### 4.7 Auswirkungen auf Backup/Restore

- Verändert die Änderung das Backup-Manifest-Schema?
- Muss ein bestehender Restore-Pfad angepasst werden?
- Bleibt `BackupRestoreService.verify_backup()` mit dem neuen Stand konsistent?
- Muss ein Restore-Truth-Test nach der Änderung neu ausgeführt werden?

---

## 5. Risk Matrix (Pflichtartefakt)

Die Risk Matrix klassifiziert jeden betroffenen Bereich nach Eintrittswahrscheinlichkeit × Schwere.

**Format:**

```
| Bereich              | Risiko                                    | W  | S  | Score | Mitigation              |
|---|---|---|---|---|---|
| postgres_truth       | Test X bricht durch Schema-Delta          | H  | H  | KRIT  | Test anpassen vor Merge |
| Recovery             | Advisory-Lock-Scope-Kollision             | M  | H  | HOCH  | Lock-Scope-Review       |
| Drift                | neuer Status nicht in EntropyMetrics      | L  | M  | MED   | entropy_helpers update  |
| Retrieval            | FTS-Index invalide nach Migration         | L  | H  | HOCH  | REINDEX nach Migration  |
| Queue                | Dead-Letter-Pfad fehlt für neuen Typ      | M  | M  | MED   | Dead-Letter-Test        |
| Citations            | Snapshot-Join bricht nach Rename          | L  | H  | HOCH  | Longevity-Test update   |
| Backup               | Manifest-Schema inkompatibel              | L  | M  | MED   | Verify-Test re-run      |
```

Legende: W = Wahrscheinlichkeit (H/M/L), S = Schwere (H/M/L), Score = KRIT/HOCH/MED/NIED

**Gate-Regel:**

- Score `KRIT`: Merge ist blockiert bis Mitigation vollständig umgesetzt und verifiziert
- Score `HOCH`: Mitigation muss im selben PR enthalten sein
- Score `MED`: Mitigation kann als Follow-up-Task geplant werden, muss aber dokumentiert sein
- Score `NIED`: kein Pflicht-Follow-up

---

## 6. Truth-Test-Plan (Pflichtartefakt)

Der Truth-Test-Plan beschreibt, welche Tests vor dem Merge grün sein müssen. Quelle: `reports/current/masterplan_status.json`.

**Pflichtinhalt:**

```
Betroffene Test-Dateien:
  - backend/tests/postgres_truth/test_XYZ_truth.py
  - (neue Test-Datei falls erforderlich)

Neue Tests erforderlich:
  - TestXYZ.test_scenario_A: beschreibt was verifiziert wird
  - (oder: keine neuen Tests erforderlich, Begründung: ...)

Ausführungsbefehl:
  pytest -m postgres_truth tests/postgres_truth -q

Erwartetes Ergebnis:
  - alle bisherigen Tests grün
  - neue Tests grün
  - keine Skips außer bei fehlender TEST_DATABASE_URL

Gate-Bedingung:
  reports/current/m4_truth_report.json: passed = N, failed = 0, skipped = 0
```

**Sonderregel für Schemaänderungen:** Jede neue Alembic-Migration muss vor Merge gegen eine echte PostgreSQL-Instanz mit `alembic upgrade head` erfolgreich durchlaufen. Ein Mock-Lauf reicht nicht.

---

## 7. Rollback-Plan (Pflichtartefakt)

Jede Architekturänderung muss einen ausführbaren Rollback-Plan enthalten.

**Pflichtinhalt:**

```
Rollback-Trigger:
  - Bedingung, unter der Rollback ausgelöst wird (z.B. "Truth-Gate FAIL nach Deploy")

Rollback-Schritte:
  1. alembic downgrade <previous_revision> (falls Schema-Änderung)
  2. Service-Deployment zurückrollen (Schritt: ...)
  3. Verifikation: (Schritt: ...)

Datenverlust-Risiko:
  - keine / low / medium / high + Begründung

Rollback-Testbarkeit:
  - Wurde der Rollback-Pfad lokal getestet? ja/nein
  - Besteht ein Migration-Downgrade-Test? ja/nein
```

**Sonderregel für irreversible Migrationen:** Wenn eine Migration nicht rückwärts-kompatibel ist (z.B. NOT NULL ohne DEFAULT, Spalten-Drop), muss der Rollback-Plan explizit dokumentieren, welche Daten verloren gehen und warum das akzeptabel ist.

---

## 8. Change-Control-Prozess

### Phase 1: Ankündigung

Vor Beginn der Implementierung:

1. Änderungsabsicht in einem Satz formulieren
2. Geltungsbereich prüfen (Abschnitt 1): Ist die Änderung governance-pflichtig?
3. Falls governance-pflichtig: alle Pflichtartefakte aus Abschnitt 3 anlegen

### Phase 2: Bewertung

Vor dem ersten Commit:

1. Alle 7 Impact-Bereiche mit expliziter Einschätzung befüllen
2. Risk Matrix erstellen (Abschnitt 5)
3. KRIT-Risiken identifizieren — falls vorhanden: Mitigation definieren, bevor Code geschrieben wird
4. Truth-Test-Plan erstellen: welche Tests sind betroffen, welche müssen neu geschrieben werden?
5. Rollback-Plan erstellen

### Phase 3: Implementierung

Während der Implementierung:

1. Schemaänderungen nur als Alembic-Migration mit korrektem Namens-Präfix
2. Neue Tests parallel zur Implementierung schreiben, nicht nachträglich
3. Keine Änderung an `GENERATED ALWAYS AS`-Spalten in INSERT/UPDATE
4. Advisory-Lock-Scope-Änderungen als explizites Commit mit Kommentar
5. Jeder neue Lifecycle-Übergang braucht einen expliziten Test in `postgres_truth`

### Phase 4: Verifikation

Vor dem Merge:

1. postgres_truth-Lauf mit `TEST_DATABASE_URL` gesetzt: alle Tests grün, keine Skips
2. `reports/current/m4_truth_report.json` aktualisiert: `failed = 0`, `skipped = 0`
3. `scripts/validate_m4_truth_gate.py` gibt `PASS` zurück
4. Alle KRIT- und HOCH-Mitigationen aus der Risk Matrix sind umgesetzt
5. Rollback-Pfad ist dokumentiert und (wenn möglich) lokal getestet

### Phase 5: Dokumentation

Nach dem Merge:

1. `docs/status.md` aktualisieren: neuer Implementierungsstand
2. `docs/postgres-truth-tests.md` aktualisieren: neue Test-Dateien und Marker
3. `masterplan.md` aktualisieren: neuer Stand unter Implemented
4. Falls API-Änderung: `docs/api/` aktualisieren
5. Falls neue Admin-Endpunkte: Admin-API-Tabelle in `docs/status.md` aktualisieren

---

## 9. Pflichtprüfungen — Kurzreferenz

Vor jedem Merge einer governance-pflichtigen Änderung müssen alle folgenden Punkte explizit bestätigt werden:

```
[ ] Impact Assessment vollständig (alle 7 Bereiche bewertet)
[ ] Jeder Bereich mit Einschätzung und Begründung (`keine` ist begründet)
[ ] Risk Matrix erstellt, alle KRIT-Mitigationen umgesetzt
[ ] Truth-Test-Plan ausgeführt: postgres_truth grün mit TEST_DATABASE_URL
[ ] Keine bestehenden Truth-Tests durch Änderung rot gemacht
[ ] Neue Tests für neue Szenarien geschrieben
[ ] Rollback-Plan dokumentiert
[ ] Alembic-Migration mit korrektem Präfix und gegen echte PostgreSQL getestet
[ ] Keine GENERATED ALWAYS AS-Spalten in INSERT/UPDATE
[ ] Kein neuer Queue-Typ ohne Dead-Letter-Pfad
[ ] Keine Lifecycle-Änderung ohne expliziten Truth-Test
[ ] Keine implizite Lifecycle-Änderung durch Schema, Service-Contract oder Admin-API
[ ] Dokumentation aktualisiert (status.md, postgres-truth-tests.md, masterplan.md)
```

---

## 10. Klassifizierung nach Änderungstyp

Die folgenden Änderungstypen definieren Zusatzprüfungen. Sie ersetzen nie die vollständige Bewertung aller 7 Impact-Bereiche aus Abschnitt 4.

### Schemaänderung (höchste Risikostufe)

Zusatzpflicht: Truth-Test-Lauf + Rollback-Plan mit Downgrade-Test.

Kritische Sonderregeln:
- `search_vector` (GENERATED ALWAYS AS) nie in INSERT/UPDATE
- NOT NULL ohne DEFAULT braucht explizite Datenverlust-Bewertung
- Jede neue Tabelle braucht eine Überprüfung auf Orphan-Risiko

### Service-Contract-Änderung

Zusatzpflicht: Schwerpunktprüfung für postgres_truth, Recovery und Queue-Konsistenz + Truth-Test-Lauf für betroffene Services.

Kritische Sonderregel: Dependency-Injection-Ketten für `get_cleanup_governance_service`, `get_reindex_governance_service`, `get_queue_aging_service`, `get_citation_longevity_service` dürfen nicht stillschweigend geändert werden.

### Lifecycle-Logik-Änderung

Zusatzpflicht: Schwerpunktprüfung für postgres_truth, Recovery, Drift, Retrieval Quality und Historical Citations + expliziter Truth-Test für alle betroffenen Übergänge.

Kritische Sonderregel: Jeder neue Lifecycle-Status muss in `EntropyMetrics` und `collect_metrics()` in `entropy_helpers.py` berücksichtigt werden.

### Queue-Änderung

Zusatzpflicht: Schwerpunktprüfung für postgres_truth und Queue-Konsistenz + Dead-Letter-Pfad-Test + Queue-Aging-Test-Update.

Kritische Sonderregel: Neue Job-Typen müssen in `inject_retryable_jobs` und `inject_dead_letter_jobs` abbildbar sein.

### Admin-API-Änderung

Zusatzpflicht: Schwerpunktprüfung für postgres_truth und Backup/Restore + Auth-Gate-Test (owner/admin only) + read-only vs. mutierend explizit dokumentieren.

Kritische Sonderregel: Keine mutierende Admin-Aktion ohne `dry_run_only=True`-Default und Safety-Gate-Prüfung.

---

## 11. Beziehung zu bestehenden Governance-Dokumenten

| Dokument | Verhältnis |
|---|---|
| `docs/operational-truth-governance.md` | Übergeordnete Truth-Quellen-Governance; dieses Dokument konkretisiert den Änderungsprozess |
| `docs/schema-evolution-safety-model.md` | Detaillierte Risiko-Klassen und Migrations-Governance für Schemaänderungen |
| `docs/data-model-invariants.md` | Invarianten INV-001 bis INV-020, die durch Schemaänderungen nicht verletzt werden dürfen |
| `docs/m4-m5-freigabefassung.md` | Gate-Freigabestand; wird durch erfolgreiche Change-Control-Prozesse aktualisiert |
| `backend/pyproject.toml` markers | Neue Marker müssen vor neuen Test-Dateien registriert werden |
| `scripts/validate_m4_truth_gate.py` | Verbindlicher Validator; PASS ist Gate-Bedingung | Quelle: `reports/current/masterplan_status.json`.

---

## 12. Verstöße und Eskalation

Ein Merge ohne vollständigen Change-Control-Prozess für eine governance-pflichtige Änderung ist ein **Gate-Blocker** für alle nachfolgenden Milestones.

Wenn eine Änderung rückwirkend als governance-pflichtig erkannt wird:

1. Impact Assessment nacherstellen
2. Fehlende Tests sofort hinzufügen
3. Truth-Lauf ausführen
4. Falls Tests rot: Rollback oder sofortiger Fix, kein Weiterbetrieb im aktuellen Zustand
5. `docs/status.md` mit korrekter Bewertung aktualisieren
