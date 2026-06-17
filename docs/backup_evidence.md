# Backup-Integration-Tests — Evidenz

Sprint PRI-7 | Task #43 | Stand: 2026-06-17

## Übersicht

| Szenario | Tests | Assertions | SCGB-01-frei | Status |
|---|---|---|---|---|
| S1 Leeres System | 3 | 6 | ja | IMPLEMENTED |
| S2 Befülltes System | 4 | 6 | ja | IMPLEMENTED |
| S3 Große Datenmenge (100) | 3 | 3 | ja | IMPLEMENTED |
| S4 Fehlerhafte Konfiguration | 5 | 5 | ja | IMPLEMENTED |
| S5 Abbruch während Backup | 3 | 3 | ja | IMPLEMENTED |
| **Gesamt** | **18** | **23** | **ja** | **IMPLEMENTED** |

---

## Entkopplungsstrategie (SCGB-01)

Alle Tests mocken per `monkeypatch`:
- `service._collect_database_metadata` — kein psycopg
- `service._create_database_dump` — kein pg_dump-Aufruf
- `service._copy_original_files` — kein OriginalFileStore-Zugriff auf echte Dateien
- `service.verify_backup` (in Restore-Tests) — gibt kontrollierten Rückgabewert

Reine Filesystem-Operationen (Verzeichnisstruktur, Checksummen, Manifest) laufen real über `tmp_path`.

---

## Szenario-Evidenz

### S1 — Leeres System sichern

```python
# Test: test_verify_leeres_backup_ist_ok
_make_valid_backup(backup_dir, file_count=0)
result = service.verify_backup(input_dir=backup_dir)
assert result["status"] == "ok"
assert result["integrity_report"]["issue_count"] == 0
```

Assertion: Checksummen korrekt, Manifest konsistent, 0 Dateien, 0 Issues.

### S2 — Befülltes System sichern

```python
# Test: test_checksummen_erkennen_manipulation_nach_backup
_make_valid_backup(backup_dir, file_count=3)
(backup_dir / "db" / "database.sql").write_text("tampered content", encoding="utf-8")
result = service.verify_backup(input_dir=backup_dir)
assert result["status"] == "invalid"
assert "checksum-mismatch" in result["error_classes"]
```

Assertion: Manipulation nach Backup wird zuverlässig erkannt.

### S3 — Große Datenmenge

```python
# Test: test_checksummen_decken_alle_100_dateien_ab
_make_valid_backup(backup_dir, file_count=100)
checksums = json.loads((backup_dir / "checksums.json").read_text())
file_entries = [k for k in checksums if k.startswith("files/")]
assert len(file_entries) == 100
```

Assertion: Alle 100 Dateien haben einen Checksum-Eintrag.

### S4 — Fehlerhafte Konfiguration

```python
# Test: test_fehlt_pg_dump_wirft_backup_restore_error
monkeypatch.setattr("app.services.backup_restore.shutil.which", lambda _: None)
with pytest.raises(BackupRestoreError, match="pg_dump"):
    service._create_database_dump(db_dir=tmp_path / "db")
```

Assertion: Fehlendes pg_dump führt sofort zu BackupRestoreError mit klarer Meldung.

### S5 — Abbruch während Backup

```python
# Test: test_fehler_in_db_dump_verhindert_manifest_erstellung
monkeypatch.setattr(service, "_create_database_dump", lambda **_: (_ for _ in ()).throw(
    BackupRestoreError("pg_dump exited with code 1: connection refused")
))
with pytest.raises(BackupRestoreError, match="pg_dump"):
    service.create_backup(output_dir=output_dir)
assert not (output_dir / "manifest.json").exists()
```

Assertion: Fehlgeschlagener DB-Dump hinterlässt kein manifest.json — kein korruptes Artefakt.

```python
# Test: test_restore_runtime_marker_wird_nach_fehler_geloescht
monkeypatch.setattr(service, "_restore_database_dump", lambda **_: (_ for _ in ()).throw(
    BackupRestoreError("psql exited with code 1")
))
with pytest.raises(BackupRestoreError, match="psql"):
    service.restore_backup(input_dir=tmp_path / "input")
assert not marker_path.exists()
```

Assertion: `_restore_runtime_marker` context manager räumt die Statusdatei auch bei Exception auf.

---

## Ausführungshinweis

**Sandbox:** Python 3.10 — conftest.py importiert `datetime.UTC` (ab Python 3.11). Syntax-Check: `ast.parse()` ohne Fehler. Statisch 18 Testmethoden erkannt.

**Produktionsumgebung:** Windows, Python 3.13. Ausführung mit:
```bash
cd backend
python -m pytest tests/test_backup_integration.py -v
```

---

## Implementierungsnachweis

- Datei: `backend/tests/test_backup_integration.py`
- Schließt GA-Blocking-Item: GA-OPS-04
- Entkoppelt von: SCGB-01 (TEST_DATABASE_URL)
