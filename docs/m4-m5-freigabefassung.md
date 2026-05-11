# M4/M5 Freigabefassung

Stand: 2026-05-11

Zweck: Dieses Dokument enthaelt nur den aktuell freigabefaehigen Wahrheitsstand fuer M4 und M5. Historische Zwischenstaende, ueberholte Scores und Zielbilder ohne aktuellen Nachweis sind bewusst ausgeschlossen.

## Aktueller Entscheidungsstand

- Der aktuelle PostgreSQL-Truth-Report ist gruen.
- Der reale M4e-Minimal-Nachweis ist erbracht.
- M4 ist fuer den lokalen Produktbetrieb nun technisch abgeschlossen.
- M4-Freigabe darf nur aus `reports/postgres_truth_report.json` plus `scripts/validate_m4_truth_gate.py` abgeleitet werden.
- Der aktuelle Validator meldet `M4-Gate PASS`.
- M5-Vorbereitung ist erlaubt.
- Produktionshaertung, Backup-Sicherheit und vollstaendige Dokumentationssynchronisierung bleiben Nachlaufpunkte, aber keine technischen M4-Blocker mehr.

## Aktuell beweisbare Aussagen

- Der technische Backend-Kern fuer M4a Auth und Workspace-Kontext ist vorhanden.
- Upload, Search, Chat und Diagnostics verwenden den aktuellen serverseitig aufgeloesten Request-Kontext.
- M4a ist ueber den aktuellen Truth-Nachweis freigabefaehig.
- M4b ist ueber den aktuellen Truth-Nachweis freigabefaehig.
- M4c ist ueber den aktuellen Truth-Nachweis freigabefaehig.
- M4d ist im read-only Scope freigabefaehig.
- M4d full mit mutierenden Admin-Aktionen ist nicht freigegeben.
- M4e ist vor M5 im Minimal-Scope erforderlich und praktisch nachgewiesen.
- `GET /api/v1/admin/diagnostics` ist als read-only Endpunkt real implementiert.
- `GET /api/v1/admin/search-index/inconsistencies` ist als read-only Diagnosequelle real implementiert.
- `POST /api/v1/admin/search-index/rebuild` ist aktuell nicht freigegeben und liefert `501 ADMIN_ACTION_NOT_IMPLEMENTED`.
- Mutierende Admin-Aktionen wie Reindex, Cleanup, Backup, Restore, Repair, User- oder Workspace-Verwaltung sind nicht als allgemeine Admin-Funktionen freigegeben.
- Historische Chat-Citations bleiben fuer archivierte oder geloeschte Dokumente sichtbar.
- Search und neues Chat-Retrieval arbeiten nur auf aktiven Dokumenten.

## Nachweisgrenzen

- Die PostgreSQL-Truth-Suite ist vorhanden; der aktuelle Gate-Status kommt ausschliesslich aus `reports/postgres_truth_report.json`.
- Der aktuelle Truth-Report ist vollstaendig gruen (`33/33`, `failed = 0`, `errors = 0`, `skipped = 0`).
- Der reale Restore-Truth-Nachweis fuer M4e ist separat in `reports/restore_truth_report.md` dokumentiert.
- Die aktuelle Freigabe gilt fuer den lokalen M4-Minimalscope, nicht fuer einen produktionsreifen Enterprise-Betrieb.

## Freigabeaussagen, die nicht verwendet werden duerfen

- M4d ist vollstaendig abgeschlossen.
- Mutierende Admin-Aktionen sind freigegeben.
- M4e ist produktionsreif abgeschlossen.
- M5 kann ohne Dokumentations- und Sicherheitsnachlauf in Produktion gehen.
- Ein manueller Score kann M4 freigeben.

## Minimale Freigabelogik ab heute

1. M4 bleibt blockiert, solange `scripts/validate_m4_truth_gate.py` auf Basis von `reports/postgres_truth_report.json` nicht `M4 Stabilization Gate = PASS` liefert.
2. M4 bleibt blockiert, solange der echte PostgreSQL-Truth-Nachweis nicht gruen ist.
3. M4d bleibt auf read-only begrenzt, bis M4a, M4b und M4c gruene Gates haben.
4. M5-Vorbereitung ist erlaubt, wenn Truth-Gate und M4e-Minimal-Nachweis gruene Evidenz haben.
5. Produktionsfreigaben bleiben zusaetzlich an Sicherheits- und Dokumentationsnachlauf gebunden.

## Entscheidungsmatrix fuer M4d Full Admin Actions

| Admin-Aktion | M4d read-only | Entscheidung | Zielzustand |
|---|---|---|---|
| Reindex ausloesen | nicht enthalten | blockiert in M4d full; fuer M4e-Minimal nur als technischer Restore-Folgeschritt noetig, nicht als freigegebene normale Admin-Aktion | operative Freigabe nach M5 |
| Cleanup ausloesen | nicht enthalten | blockiert | nach M5 verschieben |
| Backup ausloesen | nicht enthalten | blockiert als normale M4d-Admin-Aktion; fuer M4e-Minimal funktional noetig, bevorzugt ueber CLI oder Runbook statt Web-Admin | M4e-Minimal vor M5, Admin-Freigabe nach M5 |
| Repair Jobs | nicht enthalten | blockiert | nach M5 verschieben |
| Userverwaltung | nicht enthalten | blockiert | nach M5 verschieben |

Ableitung:

- M4d read-only gilt als abgeschlossen bzw. vorbereitet fuer Diagnose-Endpunkte ohne Mutation.
- M4d full bleibt bewusst `No-Go`.
- Vor M5 sind nur die fuer M4e-Minimal zwingenden Betriebsfaehigkeiten zulaessig: Backup erzeugen und Reindex nach Restore.
- Diese M4e-Minimal-Faehigkeiten werden nicht als allgemeine M4d-Full-Admin-Freigabe gewertet.

Aktueller M4e-Implementierungsstand:

- `python -m app.cli backup create|validate|restore` ist als CLI-first Codepfad vorhanden.
- Technische Originaldatei-Kopien werden im Importpfad persistiert und in den Versions-Metadaten referenziert.
- Fokussierte Unit-Tests fuer Dateiablage, Backup-Validierung und Restore-Orchestrierung sind vorhanden.
- Ein praktischer Restore-Nachweis gegen eine leere reale lokale PostgreSQL-Ziel-DB ist erbracht.

Finaler M4e-Minimal-Scope:

- PostgreSQL-DB-Dump
- technische Originaldatei-Kopien
- Konfigurationsartefakt
- Restore auf leere Zielumgebung
- Reindex nach Restore
- Wiederherstellung von Dokumenten, Versionen, Chunks, Chat-Sessions, Citations und Queue-Jobs

Expliziter Nicht-Scope fuer M4e-Minimal:

- inkrementelle Backups
- Multi-Region
- automatische Cloud-Replikation
- Zero-Downtime-Restore
- Point-in-Time-Recovery

Gate-Regeln fuer M4e-Minimal:

- vollstaendiger Restore ist praktisch nachweisbar
- `postgres_truth` ist nach Restore erneut gruen

## Harte Exit Criteria (M4 Stabilization Sprint)

Die vollstaendige Definition steht in `docs/m4-stabilization-exit-criteria.md`.

Kurzfassung — alle Bedingungen muessen gleichzeitig erfuellt sein:

| Kriterium | Wert |
|---|---|
| `postgres_truth` passed == collected | Pflicht |
| `postgres_truth` failed = 0, errors = 0, skipped = 0 | Pflicht |
| pytest exit_code = 0 | Pflicht |
| M4a Gate Score | >= 95% |
| M4b Gate Score | >= 90% |
| M4c Gate Score | >= 90% |
| M4d Gate Score (read-only) | >= 85% |
| RC-Blocker Race Condition | geschlossen |
| RC-Blocker Cross-Workspace Leak | geschlossen |
| RC-Blocker Dead-Letter Replay Verlust | geschlossen |
| RC-Blocker source_status Inkonsistenz | geschlossen |
| Masterplan referenziert latest Truth-Report | manuell bestaetigt |
| Keine unbelegten gruenen Aussagen | manuell bestaetigt |

Letzter bekannter Report: `reports/postgres_truth/latest.json`
Commit: b07798e2a9b9300aee15edfe48de82f160c3a3b3 (2026-05-11T08:14:50Z)
Aktueller Stand: Truth-Gate `PASS`, M4e-Minimal-Nachweis erbracht, M4 fuer lokalen Betrieb technisch abgeschlossen.

## Finale M4 Matrix am 2026-05-11

Formale Gate-Quellen:

- `reports/postgres_truth_report.json`
- `docs/status.md`
- `masterplan.md`
- diese Freigabefassung

Finale Matrix:

| Voraussetzung | Soll | Ist | Ergebnis |
|---|---|---|---|
| postgres_truth `passed = collected` | Pflicht | `33 = 33` | PASS |
| postgres_truth `failed = 0` | Pflicht | `0` | PASS |
| postgres_truth `errors = 0` | Pflicht | `0` | PASS |
| postgres_truth `skipped = 0` | Pflicht | `0` | PASS |
| pytest `exit_code = 0` | Pflicht | `0` | PASS |
| M4a Auth/Workspace | Truth-Gate gruen, keine offenen Gate-Blocker | `ja` | PASS |
| M4b Upload/Queue | Truth-Gate gruen, keine offenen Gate-Blocker | `ja` | PASS |
| M4c Lifecycle/Retrieval | Truth-Gate gruen, keine offenen Gate-Blocker | `ja` | PASS |
| M4d read-only | read-only Slice real vorhanden und dokumentiert | `ja` | PASS |
| M4e Minimal | echter Restore-Truth-Nachweis vorhanden | `ja` | PASS |
| Masterplan aktuell | Pflicht | `ja` | PASS |
| `docs/status.md` synchronisiert | Pflicht | `nachgezogen` | PASS |
| keine falschen gruenen Aussagen | Pflicht | `ja` | PASS |
| Truth-Report referenziert | Pflicht | `ja` | PASS |
| Restore-Truth-Report referenziert | Pflicht | `ja` | PASS |

Bewertung:

| Bereich | Ist | Gate | Ergebnis |
|---|---:|---:|---|
| M4a Auth/Workspace Isolation | 96 | 95 | PASS |
| M4b Upload/Queue | 92 | 90 | PASS |
| M4c Lifecycle/Retrieval | 95 | 90 | PASS |
| M4d Diagnostics read-only | 88 | 85 | PASS |
| M4e Backup/Restore minimal | 86 | 85 | PASS |

Entscheidung:

- M4 abgeschlossen: `ja`
- M4 technisch abgeschlossen: `ja`
- M4 blockiert: `nein`
- M5 Vorbereitung: `Go`

Praezisierung:

- Die Freigabe gilt fuer den lokalen M4-Minimalscope.
- M4d full mit mutierenden Admin-Aktionen bleibt weiterhin `No-Go`.
- Produktionshärtung fuer Backup-Sicherheit und Vollbetrieb bleibt ein Nachlaufthema ausserhalb dieses M4-Abschlusses.
