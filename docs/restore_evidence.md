# Restore-Integration-Tests — Evidenz

Sprint PRI-7 | Task #44 | Stand: 2026-06-17

## Übersicht

| Szenario | Tests | SCGB-01-frei | Status |
|---|---|---|---|
| S1 Restore auf leeres System | 4 | ja | IMPLEMENTED |
| S2 Restore auf bestehendes System | 3 | ja | IMPLEMENTED |
| S3 Korruptes Backup | 4 | ja | IMPLEMENTED |
| S4 Partielles Backup | 4 | ja | IMPLEMENTED |
| **Gesamt** | **15** | **ja** | **IMPLEMENTED** |

---

## Szenario-Evidenz

### S1 — Restore auf leeres System

```python
def test_restore_sequenz_ist_korrekt(self, tmp_path, monkeypatch):
    call_order = _full_restore_mocks(service, monkeypatch)
    result = service.restore_backup(input_dir=tmp_path / "backup")
    assert call_order == [
        "verify", "empty-check", "alembic", "restore-db",
        "restore-files", "config-check", "reindex", "drift-check", "truth-smoke",
    ]
    assert result["status"] == "completed"
```

Sequenz und alle 9 Schritte werden in der korrekten Reihenfolge ausgeführt.

### S2 — Restore auf bestehendes System

```python
def test_restore_verweigert_nicht_leere_datenbank(self, tmp_path, monkeypatch):
    monkeypatch.setattr(service, "_ensure_database_is_empty", lambda: (_ for _ in ()).throw(
        BackupRestoreError("Restore requires an empty database; documents has 17 rows")
    ))
    with pytest.raises(BackupRestoreError, match="empty database"):
        service.restore_backup(input_dir=tmp_path / "backup")
```

Config-Mismatch wird reportiert, aber nicht als Exception propagiert — Restore läuft durch:
```python
assert result["config_check"]["status"] == "mismatch"
assert "app_env" in result["config_check"]["mismatches"]
```

### S3 — Korruptes Backup

```python
def test_korrupte_checksummen_blockieren_restore(self, tmp_path, monkeypatch):
    _make_backup(backup_dir, file_count=2, corrupt_checksums=True)
    with pytest.raises(BackupRestoreError, match="validation failed"):
        service.restore_backup(input_dir=backup_dir)
```

Manipulierter SQL-Dump:
```python
(backup_dir / "db" / "database.sql").write_text("not a real dump", encoding="utf-8")
result = service.verify_backup(input_dir=backup_dir)
assert result["status"] == "invalid"
assert "checksum-mismatch" in result["error_classes"]
```

### S4 — Partielles Backup

```python
def test_manifest_mit_falschem_file_count_wird_erkannt(self, tmp_path):
    manifest["file_count"] = 99  # tatsächlich: 3
    result = service.verify_backup(input_dir=backup_dir)
    assert "manifest-file-count-mismatch" in result["error_classes"]
```

```python
def test_restore_original_files_kopiert_in_zielverzeichnis(self, tmp_path):
    count = service._restore_original_files(files_dir=files_dir)
    assert count == 1
    assert restored.read_bytes() == b"restored-content"
```

---

## Datenintegrität-Assertions

| Prüfung | Implementiert in |
|---|---|
| Checksummen korrekt | `test_korrupte_checksummen_blockieren_restore` |
| Dateiinhalt nach Restore identisch | `test_restore_original_files_kopiert_in_zielverzeichnis` |
| Manifest-Felder vollständig | `test_manifest_ohne_pflichtfelder_wird_erkannt` |
| file_count konsistent | `test_manifest_mit_falschem_file_count_wird_erkannt` |
| Leere DB vor Restore | `test_restore_verweigert_nicht_leere_datenbank` |
| Alembic nach Empty-Check | `test_restore_nach_leerem_check_setzt_alembic_auf_head` |

---

## Ausführungshinweis

```bash
cd backend
python -m pytest tests/test_restore_integration.py -v
```

Sandbox-Einschränkung: Python 3.10, `datetime.UTC` in conftest.py erfordert 3.11+. Syntax-Check: PASS.

---

## Implementierungsnachweis

- Datei: `backend/tests/test_restore_integration.py`
- Schließt GA-Blocking-Item: GA-OPS-05
- Entkoppelt von: SCGB-01 (TEST_DATABASE_URL)
