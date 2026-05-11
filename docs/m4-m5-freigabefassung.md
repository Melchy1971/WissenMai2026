# M4/M5 Freigabefassung

Stand: 2026-05-11

Zweck: Dieses Dokument enthaelt nur den aktuell freigabefaehigen Wahrheitsstand fuer M4 und M5. Historische Zwischenstaende, ueberholte Scores und Zielbilder ohne aktuellen Nachweis sind bewusst ausgeschlossen.

## Aktueller Entscheidungsstand

- Der aktuelle PostgreSQL-Truth-Report ist gruen.
- M4 ist aktuell dennoch nicht vollstaendig technisch stabilisiert.
- Manuelle Scores geben M4 nicht frei.
- M4-Freigabe darf nur aus `reports/postgres_truth_report.json` plus `scripts/validate_m4_truth_gate.py` abgeleitet werden.
- Wenn der Validator `M4 Truth Gate = FAIL` meldet, bleibt M4 blockiert; ein `PASS` hebt aber nur das Truth-Gate auf, nicht automatisch alle Restblocker.
- Das finale M4 Exit Gate ist derzeit nicht bestanden.
- M5 bleibt blockiert.
- M5 bleibt auch dann blockiert, wenn M4 spaeter technisch stabilisiert wird, solange die vollstaendige Dokumentationspruefung nicht abgeschlossen ist.

## Aktuell beweisbare Aussagen

- Der technische Backend-Kern fuer M4a Auth und Workspace-Kontext ist vorhanden.
- Upload, Search, Chat und Diagnostics verwenden den aktuellen serverseitig aufgeloesten Request-Kontext.
- M4a ist nicht abgeschlossen.
- M4b ist nicht abgeschlossen.
- M4c ist nicht abgeschlossen.
- M4d ist als read-only Diagnostics-Slice vorbereitet und fuer diesen Scope akzeptiert.
- M4d full mit mutierenden Admin-Aktionen ist nicht freigegeben.
- M4e ist vor M5 im Minimal-Scope erforderlich und aktuell nur partiell umgesetzt.
- `GET /api/v1/admin/diagnostics` ist als read-only Endpunkt real implementiert.
- `GET /api/v1/admin/search-index/inconsistencies` ist als read-only Diagnosequelle real implementiert.
- `POST /api/v1/admin/search-index/rebuild` ist aktuell nicht freigegeben und liefert `501 ADMIN_ACTION_NOT_IMPLEMENTED`.
- Mutierende Admin-Aktionen wie Reindex, Cleanup, Backup, Restore, Repair, User- oder Workspace-Verwaltung sind nicht als allgemeine Admin-Funktionen freigegeben.
- Historische Chat-Citations bleiben fuer archivierte oder geloeschte Dokumente sichtbar.
- Search und neues Chat-Retrieval arbeiten nur auf aktiven Dokumenten.

## Nachweisgrenzen

- Die PostgreSQL-Truth-Suite ist vorhanden; der aktuelle Gate-Status kommt ausschliesslich aus `reports/postgres_truth_report.json`.
- Das aktuelle Truth-Gate ist gruen, aber der Report belegt nicht automatisch die Exit-Schwellen fuer `M4a`, `M4b`, `M4c` und `M4d`.
- Search/Chat-, Lifecycle- und Upload-Race-Nachweise bleiben fuer die Exit-Bewertung nur soweit belastbar, wie sie im aktuellen Report und den synchronisierten Statusdokumenten tatsaechlich belegt sind.
- Lifecycle-Mutationen und angrenzende Produktfluesse sind fachlich gehaertet, verfehlen aber in der aktuellen Exit-Bewertung weiterhin die geforderten Zielschwellen.

## Freigabeaussagen, die nicht verwendet werden duerfen

- M4 ist abgeschlossen.
- M4 ist technisch stabilisiert.
- M4d ist vollstaendig abgeschlossen.
- Mutierende Admin-Aktionen sind freigegeben.
- Search/Chat-Konsistenz ist aktuell auf echter PostgreSQL-DB gruen bewiesen.
- PostgreSQL-Truth-Tests sind fuer den aktuellen Stand gruen nachgewiesen.
- M5 kann starten.
- Ein manueller Score kann M4 freigeben.

## Minimale Freigabelogik ab heute

1. M4 bleibt blockiert, solange `scripts/validate_m4_truth_gate.py` auf Basis von `reports/postgres_truth_report.json` nicht `M4 Stabilization Gate = PASS` liefert.
2. M4 bleibt blockiert, solange der echte PostgreSQL-Truth-Nachweis nicht gruen ist.
3. M4d bleibt auf read-only begrenzt, bis M4a, M4b und M4c gruene Gates haben.
4. M5 bleibt blockiert, bis M4 technisch stabilisiert ist.
5. M5 bleibt zusaetzlich blockiert, bis der M4e-Minimal-Scope nachweisbar erfuellt ist.
6. M5 bleibt zusaetzlich blockiert, bis die vollstaendige Dokumentationspruefung abgeschlossen ist.

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
Aktueller Stand: Truth-Gate `PASS`, finales M4 Exit Gate weiterhin `FAIL`.

## Finales M4 Exit Gate am 2026-05-11

Formale Gate-Quellen:

- `reports/postgres_truth_report.json`
- `docs/status.md`
- `masterplan.md`
- diese Freigabefassung

Exit-Gate Report:

| Voraussetzung | Soll | Ist | Ergebnis |
|---|---|---|---|
| postgres_truth `passed = collected` | Pflicht | `33 = 33` | PASS |
| postgres_truth `failed = 0` | Pflicht | `0` | PASS |
| postgres_truth `errors = 0` | Pflicht | `0` | PASS |
| postgres_truth `skipped = 0` | Pflicht | `0` | PASS |
| pytest `exit_code = 0` | Pflicht | `0` | PASS |
| M4a Score | `>= 95` | `86` | FAIL |
| M4b Score | `>= 90` | `88` | FAIL |
| M4c Score | `>= 90` | `86` | FAIL |
| M4d read-only Score | `>= 85` | aktuell nicht numerisch belegt | FAIL |
| M4e Entscheidung dokumentiert | Pflicht | `ja` | PASS |
| Masterplan aktuell | Pflicht | `ja` | PASS |
| `docs/status.md` aktuell | Pflicht | `ja, mit Restpunkten` | PASS |
| keine falschen gruenen Aussagen | Pflicht | `ja` | PASS |
| Truth-Report referenziert | Pflicht | `ja` | PASS |

Scorematrix:

| Bereich | Ist | Gate | Ergebnis |
|---|---:|---:|---|
| M4a Auth/Workspace Isolation | 86 | 95 | FAIL |
| M4b Upload-GUI | 88 | 90 | FAIL |
| M4c Dokument-Lifecycle | 86 | 90 | FAIL |
| M4d Diagnostics read-only | nicht numerisch belegt | 85 | FAIL |
| M4e Entscheidung dokumentiert | ja | Pflicht | PASS |

Entscheidung:

- M4 abgeschlossen: `nein`
- M4 teilweise abgeschlossen: `ja`
- M4 blockiert: `ja`
- M5: `No-Go`
