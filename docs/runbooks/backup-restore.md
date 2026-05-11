# Backup und Restore Runbook

Stand: 2026-05-11

## Zweck

Dieses Runbook beschreibt den operativen Zielprozess fuer M4e Backup und Restore im lokalen Produktbetrieb.

Das fachliche Konzept und die Architekturregeln stehen in [docs/m4e-backup-restore.md](H:/WissenMai2026/docs/m4e-backup-restore.md).
Das szenariobasierte Disaster-Recovery-Runbook steht in [docs/runbooks/disaster-recovery.md](H:/WissenMai2026/docs/runbooks/disaster-recovery.md).

## Betriebsziel

- Das System soll nach DB- oder Dateisystemfehlern vollstaendig wiederherstellbar sein.
- Ein Backup gilt nur dann als erfolgreich, wenn PostgreSQL-Dump, technische Originaldatei-Kopien, Konfiguration und Manifest konsistent vorliegen.
- Search-Index-Dateien sind nicht pflichtig, weil der Index rekonstruierbar ist.

## Finaler M4e-Minimal-Scope

In Scope:

- PostgreSQL-DB-Dump
- technische Originaldatei-Kopien
- Konfigurationsartefakt
- Restore auf leere Zielumgebung
- Reindex nach Restore
- Wiederherstellung von Dokumenten, Versionen, Chunks, Chat-Sessions, Citations und Queue-Jobs

Nicht-Scope:

- inkrementelle Backups
- Multi-Region
- automatische Cloud-Replikation
- Zero-Downtime-Restore
- Point-in-Time-Recovery

## Backup-Struktur

```text
backup-<timestamp>/
	manifest.json
	checksums.json
	db/
		database.sql
		pg_dump_version.txt
	files/
		<workspace_id>/<document_id>/<content_hash>/<original_filename>
	config/
		app-config.json
```

Manifest-Pflichtfelder:

- `created_at`
- `alembic_revision`
- `app_version`
- `workspace_count`
- `document_count`
- `database_dump_path`
- `pg_dump_version`

## Abgrenzung zu M4d Admin Actions

- Dieses Runbook beschreibt einen operativen M4e-Minimal-Prozess, keinen freigegebenen M4d-Full-Admin-Slice.
- M4d read-only bleibt auf Diagnose-Endpunkte ohne Mutation begrenzt.
- Mutierende Admin-Aktionen wie allgemeiner Reindex, Cleanup, Repair Jobs oder Userverwaltung bleiben durch dieses Runbook weiterhin blockiert.
- Vor M5 sind aus diesem Themenfeld nur die fuer M4e-Minimal notwendigen Betriebsfaehigkeiten zulaessig: Backup erzeugen und Search-Index nach Restore neu aufbauen.
- Diese Betriebsfaehigkeiten sollen vor M5 vorzugsweise ueber CLI und Runbook ausgefuehrt werden, nicht als allgemeine Web-Admin-Funktionen.

## Minimaler manueller Ablauf

1. Applikation in einen ruhigen Betriebszustand bringen.
2. `python -m app.cli backup create --output <path>` ausfuehren.
3. `python -m app.cli backup validate --input <path>` ausfuehren.
4. `python -m app.cli backup verify-backup --input <path>` ausfuehren.
5. Manifest, `checksums.json` und Integritaetsreport pruefen.
6. Backup-Artefakt an einen getrennten Speicherort kopieren.

## Verify-Backup Operator-Check

Zweck:

- `validate` prueft nur die Basiskonsistenz der referenzierten Dateien gegen `checksums.json`.
- `verify-backup` ist der operative Vollcheck vor Restore oder Archivierung.

CLI:

```text
python -m app.cli backup verify-backup --input <path>
```

Admin-API:

```text
POST /api/v1/admin/backup/verify
{
  "input_dir": "<path>"
}
```

Der Integritaetsreport enthaelt die folgenden Pflichtchecks:

- `db_dump_readable`: SQL-Dump vorhanden und als PostgreSQL-Dump lesbar
- `required_files_present`: Pflichtartefakte aus Backup-Struktur vorhanden
- `manifest_consistent`: Manifest-Pflichtfelder und deklarierte Datei-Anzahlen konsistent
- `checksums_valid`: Hashwerte und Checksum-Eintraege korrekt
- `upload_files_complete`: Upload-Dateipfad vorhanden
- `restore_dry_run`: Restore-Voraussetzungen technisch plausibel, inklusive `psql` und SQL-Restore-Marker

## Fehlerklassen im Integritaetsreport

Maschinenlesbare Fehlerklassen im Feld `error_classes`:

- `missing-database-dump`
- `database-dump-unreadable`
- `missing-file`
- `manifest-missing-field`
- `manifest-file-count-mismatch`
- `manifest-path-missing`
- `checksum-entry-invalid`
- `checksum-mismatch`
- `missing-upload-file`
- `restore-dry-run-failed`

Operator-Interpretation:

- `status = ok`: Backup ist fuer Restore-Vorbereitung technisch konsistent.
- `status = invalid`: Backup nicht fuer Restore freigeben, bis alle Fehlerklassen geklaert sind.
- `restore-dry-run-failed`: Restore nicht starten, bevor `psql`-Verfuegbarkeit oder Dump-Inhalt korrigiert ist.

## Minimaler Restore-Ablauf

1. Zielumgebung vorbereiten.
2. Sicherstellen, dass die Ziel-Datenbank leer ist.
3. `python -m app.cli backup verify-backup --input <path>` ausfuehren.
4. `python -m app.cli backup restore --input <path>` ausfuehren.
5. Restore-Pipeline prueft automatisch:
	- DB-Dump eingespielt
	- Dateien wiederhergestellt
	- Konfiguration gegen Snapshot geprueft
	- Search-Index rebuilt
	- Drift-Check `ok`
	- `postgres_truth` Smoke-Subset gruen
6. Integritaetspruefung starten.

## Operative Pflichtpruefungen

- Sind alle im Manifest deklarierten Dateien vorhanden?
- Ist `verify-backup` insgesamt `ok`?
- Stimmen die Hashwerte?
- Ist die Datenbank nach Restore erreichbar?
- Ist die Migration auf `head`?
- Ist der Search-Index neu baubar?
- Ist der Drift-Check nach Restore `ok`?
- Ist das `postgres_truth`-Smoke-Subset nach Restore gruen?

## Gate-Regeln

- Vollstaendiger Restore auf leere Zielumgebung ist praktisch nachgewiesen.
- Die Minimal-Datenklassen sind nach Restore wiederhergestellt: Dokumente, Versionen, Chunks, Chat-Sessions, Citations, Queue-Jobs.
- `postgres_truth` ist nach Restore erneut gruen.

## Status in M4e

- Konzept definiert
- CLI-first Codepfad fuer Backup, Validate, Restore und Reindex vorhanden
- technische Originaldatei-Kopien werden im Importpfad abgelegt
- Restore-Pipeline enthaelt nun Config-Check, Reindex, Drift-Check und `postgres_truth`-Smoke-Subset
- operative Automatisierung weiterhin nicht implementiert
- praktischer Restore-Endlauf gegen eine leere reale lokale PostgreSQL-Ziel-DB nachgewiesen
