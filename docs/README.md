# Dokumentation

Dokumentationsbereich fuer Architektur-, Entscheidungs- und Betriebswissen der Wissensbasis.

## Zweck

- Architektur und technische Leitplanken dokumentieren.
- ADRs nachvollziehbar versionieren.
- API-Notizen, Task-Kontrakte, Review-Prompts und Runbooks sammeln.
- Betriebswissen getrennt von Quellcode pflegen.

## Struktur

- `adr/`: Architekturentscheidungen.
- `api/`: Platz fuer API-Skizzen, Kontrakte und spaetere Endpunktdokumentation.
- `prompts/`: Hilfsdokumente fuer Reviews und Task-Vertraege.
- `runbooks/`: Betriebs- und Wiederherstellungsablaeufe.

Wichtige Runbooks im aktuellen Stand:

- [docs/runbooks/backup-restore.md](H:/WissenMai2026/docs/runbooks/backup-restore.md): operativer M4e-Minimalpfad fuer Backup und Restore
- [docs/runbooks/disaster-recovery.md](H:/WissenMai2026/docs/runbooks/disaster-recovery.md): szenariobasiertes DR-Runbook mit Operator-Guide und Checklisten

## Aktueller Freigabestand

Die kompakte Freigabefassung fuer den aktuell zulaessigen M4/M5-Dokumentationsstand steht in `docs/m4-m5-freigabefassung.md`.

Der aktuelle echte Restore-Truth-Nachweis steht in [reports/restore_truth_report.md](H:/WissenMai2026/reports/restore_truth_report.md).

Sie ist die bevorzugte Kurzreferenz fuer:

- aktuellen M4-Hardening-Status
- read-only-Grenze von M4d
- Gate- und Freigabestand fuer M5
- Aussagen, die aktuell nicht als freigegeben dokumentiert werden duerfen

## M5 Vorbereitung

Die folgenden Dokumente bilden den Vorbereitungsrahmen fuer M5. Sie beschreiben aktuell nur Statuslogik, Konzepte und spaetere Nachweisanker.

Sie duerfen nicht als Beleg fuer einen gestarteten M5-Betrieb, eine laufende Implementierung oder ein grünes M5-Gate gelesen werden.

- [docs/data-quality.md](H:/WissenMai2026/docs/data-quality.md): Vorbereitungsrahmen fuer M5 Data Quality
- [docs/drift.md](H:/WissenMai2026/docs/drift.md): Vorbereitungsrahmen fuer M5 Drift Detection
- [docs/cleanup.md](H:/WissenMai2026/docs/cleanup.md): Vorbereitungsrahmen fuer M5 Cleanup
- [docs/health-score.md](H:/WissenMai2026/docs/health-score.md): Vorbereitungsrahmen fuer M5 Health Score
- [docs/operations.md](H:/WissenMai2026/docs/operations.md): Betriebsrahmen inklusive M5-Dokumentationslogik
- [docs/postgres-truth-tests.md](H:/WissenMai2026/docs/postgres-truth-tests.md): Wahrheitslogik und Gate-Regeln fuer PostgreSQL-Nachweise inklusive M5-Erweiterung