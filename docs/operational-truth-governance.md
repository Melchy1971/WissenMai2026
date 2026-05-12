# Operational Truth Governance

Stand: 2026-05-12

## Ziel

Produktionsnahe Systemzustaende duerfen nicht aus Dokumentation, Absichtserklaerungen oder manuellen Statusformulierungen abgeleitet werden. Ein Status ist nur gueltig, wenn ein messbares, versioniertes und maschinenlesbares Nachweisartefakt ihn belegt.

## Governance-Regelwerk

1. Dokumentation darf Status nur referenzieren, nicht erzeugen.
2. Manuelle "gruen"-Behauptungen sind verboten.
3. Gates muessen maschinenlesbar sein.
4. Jeder kritische Status braucht ein Nachweisartefakt.
5. SQLite, In-Memory-DBs und Mocks zaehlen nie als finale Wahrheit.
6. Markdown-Reports sind menschenlesbare Begleitansichten; Gate-Entscheidungen brauchen JSON oder einen Validator mit maschinenlesbarem Input.
7. Jeder Gate-Report muss Zeitpunkt, Quelle, Exit-Code oder Status, Fehlerzaehler und Scope enthalten.
8. Fehlt ein aktueller Report, lautet der Status `unknown` oder `not_verified`, niemals `pass`.
9. Ein Health Score ersetzt kein Truth Gate.
10. Ein einzelner gruener Report darf keine nicht abgedeckten Slices freigeben.

## Truth-Quellen

| Quelle | Primaerer Zweck | Artefakt | Maschinenlesbar | Finale Wahrheit fuer |
|---|---|---|---|---|
| PostgreSQL Truth Reports | harte End-to-End-Wahrheit gegen echte PostgreSQL-Transaktionen | `reports/postgres_truth/latest.json`, versionierte `reports/postgres_truth/YYYYMMDD_HHMMSS.json` | ja | M4/M5 Truth-Gates, Setup-/Migration-/Isolation-/Recovery-Faelle |
| Drift Reports | Abweichung zwischen Sollzustand und Laufzeitzustand | geplanter `reports/m5_drift/latest.json`, bis dahin Search-Drift-API/Entropy-Report | ja erforderlich | Search/Lifecycle/Citation/Queue/Backup/Data-Quality-Drift |
| Restore Truth Reports | Wiederherstellbarkeit und Datenparitaet | `reports/restore_truth_report.md`, spaeter zusaetzlich JSON | teilweise; JSON fuer Gate erforderlich | Restore-Faehigkeit, DR-Basis, Backup-Vertrauen |
| Cleanup Truth Reports | Dry-Run- und Safety-Wahrheit fuer Cleanup | geplanter Cleanup-Report plus `postgres_truth` Cleanup-Block | ja erforderlich | Cleanup-Safety, Schutz von Citations, aktiven Daten und Queue |
| Health Score | laufende Steuerungs- und Risikometrik | geplanter `reports/m5_health/latest.json` | ja erforderlich | Betriebszustand, nicht Gate-Ersatz |
| Observability Metriken | Laufzeit- und Trenddaten | strukturierte JSON-Logs, Metrik-Snapshots, `m5_metric_observed` | ja | Trends, Alerts, Dashboard, Eskalation |

## Gate-Policies

### Allgemeine Gate-Policy

Ein Gate darf nur `pass` sein, wenn:

- die definierte Truth-Quelle existiert
- das Artefakt aktuell ist
- das Artefakt maschinenlesbar auswertbar ist
- `failed = 0`
- `errors = 0`
- `skipped = 0`, sofern es sich um ein Pflichtgate handelt
- `exit_code = 0`, falls ein Testlauf beteiligt ist
- der Scope des Artefakts den behaupteten Status abdeckt

Wenn eines dieser Kriterien fehlt:

- Gate-Status: `fail` bei verletzter Pflichtbedingung
- Gate-Status: `unknown` bei fehlendem Artefakt
- Gate-Status: `partial` bei belegtem Teilscope

### M4 Gate Policy

Quelle:

- `reports/postgres_truth/latest.json`
- `reports/postgres_truth_report.json`
- Validator: `scripts/validate_m4_truth_gate.py`

Policy:

- `test_database_url_set = true`
- `passed = collected`
- `failed = 0`
- `errors = 0`
- `skipped = 0`
- `pytest_exit_code = 0`
- `m4_gate_blockers = []`

Dokumentation darf M4 nur dann als gruen beschreiben, wenn sie diesen Report und Validatorstatus referenziert.

### M5 Gate Policy

M5 darf sliceweise nur `pass` sein, wenn der jeweilige Slice einen aktuellen Report besitzt.

| M5 Slice | Pflichtquelle | Pass-Bedingung |
|---|---|---|
| Data Quality | PostgreSQL Truth Report + Data-Quality-Report | keine Invariantenverletzung, keine Orphans, keine unklassifizierten Duplicates |
| Drift Detection | Drift Report + Postgres Truth Block | Drift Score im erlaubten Zustand, keine kritische Drift |
| Cleanup Dry-Run | Cleanup Truth Report + Postgres Truth Block | Dry Run korrekt, keine aktiven Daten/Citations/Queue-Konsistenz verletzt |
| Health Score | Health Score JSON + Quellmetriken | Score berechenbar, Quellen aktuell, fehlende Evidenz konservativ bewertet |
| Backup Freshness | Restore/Backup Verify Report | Backup aktuell, Verify erfolgreich, Restore-Nachweis im erlaubten Alter |
| Observability | Metrik-Snapshot/Log-Auswertung | alle Pflichtmetriken vorhanden, keine sensitiven Inhalte, Workspace-Aggregation korrekt |

M5-Implementierung kann kontrolliert freigegeben sein, waehrend einzelne M5-Slices noch `not_verified` oder `watch` sind. M5-Produktionsreife erfordert dagegen vollstaendig gruene Gate-Reports.

### Restore Gate Policy

Ein Restore-Gate ist nur gruen, wenn der Report belegt:

- Restore auf leere Zielumgebung
- DB-Paritaet fuer Kernobjekte
- technische Originaldateien vorhanden
- Reindex nach Restore erfolgreich
- Drift-Check ohne kritische Abweichung
- Truth-Smoke oder definierter Truth-Block gruen

Markdown-only Restore-Reports duerfen eine menschliche Freigabe stuetzen, muessen fuer zukuenftige automatisierte Gates aber durch JSON ergaenzt werden.

### Cleanup Gate Policy

Cleanup darf nur `pass` sein, wenn:

- Dry-Run-Report vorhanden
- `blocked_count = 0`
- `protected_count` nachvollziehbar ist
- keine aktive Queue-Referenz geloescht wird
- keine historische Citation geloescht oder still umgeschrieben wird
- keine aktiven Dokumente, Versionen oder Chunks geloescht werden
- PostgreSQL-only Truth-Test den Pfad belegt

Destructive Cleanup braucht ein separates Mutationsgate. Ein Dry-Run-Pass ist keine Loeschfreigabe.

### Observability Gate Policy

Observability darf nur `pass` sein, wenn:

- alle Pflichtmetriken vorhanden sind
- `workspace`-Metriken genau eine `workspace_id` tragen
- `global`-Metriken keine `workspace_id` tragen
- sensitive Felder ausgeschlossen sind
- Trends ueber definierte Fenster berechenbar sind
- Metriken auf Reports oder strukturierten Events beruhen

Verbotene sensitive Felder:

- Dokumenttext
- Chunktext
- Querytext
- Quote Preview
- Dateipfade
- Tokens
- Secrets
- freie Nutzeridentitaeten in Aggregationsmetriken

## Dokumentationsregeln

Erlaubte Formulierungen:

- `Report X weist pass aus`
- `Validator Y meldet pass`
- `Status not_verified, weil Report fehlt`
- `Vorbereitung definiert, aber nicht als Gate-Pass belegt`

Verbotene Formulierungen:

- `gruen`, ohne Reportreferenz
- `abgeschlossen`, ohne Gate-Artefakt
- `produktionsreif`, nur wegen Dokumentation
- `SQLite gruen`, als finales Gate
- `manuell validiert`, als Ersatz fuer Pflichtreport

## Statusvokabular

| Status | Bedeutung |
|---|---|
| `pass` | maschinenlesbarer Report belegt alle Pflichtbedingungen |
| `fail` | Report existiert, aber mindestens eine Pflichtbedingung ist verletzt |
| `unknown` | kein aktuelles Artefakt vorhanden |
| `partial` | Artefakt belegt nur einen Teilscope |
| `watch` | keine harte Verletzung, aber Trend/Risiko/offene Evidenz |
| `blocked` | harte Sicherheits-, Integritaets- oder Gate-Verletzung |

## SQLite-Regel

SQLite ist erlaubt fuer:

- schnelle Unit-Tests
- lokales Entwicklerfeedback
- Schema-nahe Smoke-Tests
- reine Parser-/Service-Logik ohne PostgreSQL-Verhalten

SQLite ist verboten als finale Wahrheit fuer:

- Migration-Gates
- Workspace-Isolation
- Auth-/Session-Truth
- Queue-Recovery
- advisory locks
- race conditions
- Search/Reindex-Drift
- Restore-Faehigkeit
- Cleanup-Safety
- M5-Gates

## Mindestfelder fuer Gate-Artefakte

Jedes maschinenlesbare Gate-Artefakt muss enthalten:

- `generated_at`
- `source`
- `scope`
- `status`
- `command` oder `producer`
- `database_kind`
- `test_database_url_set` falls Tests beteiligt sind
- `passed`, `failed`, `errors`, `skipped` falls Tests beteiligt sind
- `exit_code` falls Kommando beteiligt ist
- `commit_hash` falls Codezustand relevant ist
- `blocking_findings`
- `warnings`
- `evidence_links`

## Konsequenzregeln

- `fail` blockiert das zugehoerige Gate.
- `unknown` blockiert Freigaben, darf aber Vorbereitung erlauben.
- `partial` erlaubt nur Teilscope-Aussagen.
- `watch` erlaubt kontrollierte Implementierung, aber keine Produktionsfreigabe.
- `blocked` stoppt Mutation und verlangt Recovery-/Incident-Pfad.
