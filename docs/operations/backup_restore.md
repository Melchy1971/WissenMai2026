# Backup und Restore

Stand: 2026-06-17
Bezug: `docs/runbooks/backup-restore.md`, `docs/m4e-backup-restore.md`

> Grundregel: Nie auf der einzigen verbliebenen Sicherung arbeiten.
> Backup immer vor einem destruktiven Eingriff validieren.
> Restore immer gegen leere oder bewusst vorbereitete Zielumgebung ausführen.

---

## Scope

In Scope:
- PostgreSQL-DB-Dump
- Technische Originaldatei-Kopien
- Konfigurationsartefakt
- Restore auf leere Zielumgebung
- Reindex nach Restore

Nicht in Scope:
- Inkrementelle Backups
- Multi-Region / Cloud-Replikation
- Zero-Downtime-Restore
- Point-in-Time-Recovery

---

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

Pflichtfelder in `manifest.json`:
- `created_at`, `alembic_revision`, `app_version`
- `workspace_count`, `document_count`
- `database_dump_path`, `pg_dump_version`

---

## Backup erstellen

```powershell
# Konfiguration pruefen
# BACKUP_RESTORE_ROOT_DIR und BACKUP_TARGET_PATH muessen in .env gesetzt sein

# Backup ausfuehren
python -m app.cli backup create --output $env:BACKUP_TARGET_PATH

# Backup validieren (immer direkt nach Erstellung)
python -m app.cli backup validate --input <backup-pfad>
```

Backup gilt als erfolgreich erst nach fehlerfreier Validierung.
Ergebnis protokollieren: Zeitpunkt, Pfad, `alembic_revision`, `document_count`.

---

## Backup validieren

```powershell
python -m app.cli backup validate --input <backup-pfad>
```

Prüft:
- Manifest vollständig und lesbar
- Checksummen stimmen
- DB-Dump vorhanden und nicht leer
- Konfigurationsartefakt vorhanden

Exit 0 = valide. Exit != 0 = Backup unbrauchbar, kein Restore durchführen.

---

## Restore durchführen

Voraussetzung: Backup validiert (Exit 0), zweite Person anwesend.

```powershell
# Schritt 1: Ziel-DB leeren oder neu anlegen
psql -U postgres -c "DROP DATABASE IF EXISTS wissensbasis_restore;"
psql -U postgres -c "CREATE DATABASE wissensbasis_restore;"

# Schritt 2: DATABASE_URL in .env auf Ziel-DB setzen
# DATABASE_URL=postgresql+psycopg://wissensbasis:change-me@127.0.0.1:5432/wissensbasis_restore

# Schritt 3: Restore
python -m app.cli backup restore --input <backup-pfad>

# Schritt 4: Reindex (Such-Index ist nicht im Backup, muss neu aufgebaut werden)
python -m app.cli search rebuild-index

# Schritt 5: Drift-Check
cd backend && .venv\Scripts\python -m drift.cli run

# Schritt 6: Standard-Validierung
Invoke-RestMethod http://localhost:8000/health/db
python scripts/check_auth_bootstrap.py --no-start-api
pytest -m postgres_truth tests/postgres_truth/test_smoke.py -vv
```

---

## Post-Restore Checkliste

- [ ] Backup vor Restore validiert (Exit 0)
- [ ] Zweite Person war anwesend
- [ ] Restore in leere Zielumgebung ausgeführt
- [ ] Dokumente lesbar (Dokumentliste über API erreichbar)
- [ ] Search liefert erwartete Treffer
- [ ] Chat Retrieval liefert konsistente Citations
- [ ] Lifecycle-Zustände konsistent
- [ ] Historical Citations tragen korrekten `source_status`
- [ ] Queue-Zustände konsistent
- [ ] Drift-Check: `ok`
- [ ] `postgres_truth`-Smoke-Subset grün
- [ ] Audit-Log-Eintrag geschrieben (Zeitpunkt, Operator, verwendetes Backup, Abweichungen)

---

## Disaster Recovery — Schwere Störungsszenarien

### Datenbank zerstört

Symptome: Backend startet nicht, `alembic current` schlägt fehl, Auth/Search/Chat fallen gleichzeitig aus.

Vorgehen:
1. Letztes gültiges Backup identifizieren (Manifest-Datum + `alembic_revision` prüfen)
2. `python -m app.cli backup validate --input <path>` → muss Exit 0 ergeben
3. Ziel-DB neu erzeugen (leere DB)
4. `python -m app.cli backup restore --input <path>`
5. Post-Restore-Checkliste abarbeiten

Datenverlust-Risiko: abhängig vom Abstand zwischen letztem Backup und Ausfallzeitpunkt.
Dauer: 15–45 Minuten bei vorhandenem Backup und erreichbarer Ziel-DB.

### Dateisystem-Verlust (Original Files)

Symptome: Dokument-Downloads schlagen fehl, `original_file_store_dir` nicht erreichbar.

Vorgehen:
1. `ORIGINAL_FILE_STORE_DIR` aus `.env` lesen
2. Backup-Kopie aus `files/`-Unterverzeichnis des Backups wiederherstellen
3. Pfadstruktur muss erhalten bleiben: `<workspace_id>/<document_id>/<content_hash>/<original_filename>`
4. Nach Wiederherstellung: Dokument-Download für Stichproben testen

### Konfigurationsverlust

Symptome: Backend startet mit falschen Defaults, Workspace-ID oder Admin-Token stimmt nicht.

Vorgehen:
1. `config/app-config.json` aus letztem Backup lesen
2. `.env` entsprechend ergänzen
3. Backend neu starten, Standard-Validierung ausführen

---

## Umgebungsvariablen für Backup/Restore

| Variable | Zweck | Default |
|----------|-------|---------|
| `BACKUP_TARGET_PATH` | Zielverzeichnis für Backups | (muss gesetzt sein) |
| `BACKUP_RESTORE_ROOT_DIR` | Root-Verzeichnis für Restore-Operationen | (muss gesetzt sein) |
| `ORIGINAL_FILE_STORE_DIR` | Speicherort technischer Originaldateien | (muss gesetzt sein) |

Alle drei müssen in `.env` gesetzt sein, bevor Backup/Restore ausgeführt wird.
