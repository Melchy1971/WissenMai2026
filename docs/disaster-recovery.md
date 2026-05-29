# Disaster Recovery Runbook

Dieses Runbook beschreibt die wichtigsten Wiederherstellungsmaßnahmen für typische Ausfallszenarien im WissenMai2026-System. Für jedes Szenario werden Symptom, Diagnose, Ursache, Recovery-Schritte und Validierung beschrieben.

---

## 1. PostgreSQL beschädigt
**Symptom:**
- Backend/API wirft Datenbankfehler, keine Verbindung möglich

**Diagnose:**
- Fehlermeldung: "could not connect to server" oder "database disk image is malformed"
- PostgreSQL-Logs prüfen (`docker logs docstore_db` oder `journalctl -u postgresql`)

**Ursache:**
- Dateisystemfehler, Hardwaredefekt, fehlerhafte Migration, Stromausfall

**Recovery:**
1. PostgreSQL stoppen (`docker stop docstore_db` oder `systemctl stop postgresql`)
2. Letztes valides Backup bereitstellen
3. Datenverzeichnis sichern (`cp -r /var/lib/postgresql/data /tmp/defekt-backup`)
4. Backup zurückspielen (siehe Restore-Anleitung)
5. PostgreSQL starten

**Validierung:**
- `operations_selftest.ps1` ausführen, alle Checks müssen PASS sein

---

## 2. PostgreSQL gelöscht
**Symptom:**
- Datenbankdienst startet nicht, Daten fehlen komplett

**Diagnose:**
- Datenverzeichnis leer oder nicht vorhanden
- Fehlermeldung: "database does not exist"

**Ursache:**
- Manuelles Löschen, fehlerhafte Container-Neuerstellung, Volume entfernt

**Recovery:**
1. Neues Datenverzeichnis initialisieren (z.B. `docker volume create`)
2. PostgreSQL neu starten
3. Letztes valides Backup zurückspielen
4. Alembic Migrationen prüfen (`alembic heads`)

**Validierung:**
- Seed User vorhanden, Login möglich, Selftest PASS

---

## 3. Seed User fehlt
**Symptom:**
- Login mit Standard-Account nicht möglich

**Diagnose:**
- Query: `SELECT * FROM users WHERE is_default = true;` ergibt keine Treffer

**Ursache:**
- Fehler beim Seeding, versehentlich gelöscht

**Recovery:**
1. Seed-Skript erneut ausführen (`python -m app.scripts.seed_auth`)
2. Backend neu starten

**Validierung:**
- Seed User existiert, Login erfolgreich

---

## 4. Migration fehlgeschlagen
**Symptom:**
- Alembic Fehler, Backend startet nicht, DB-Inkonsistenzen

**Diagnose:**
- `alembic heads` oder `alembic upgrade head` schlägt fehl
- Fehlermeldung im Log prüfen

**Ursache:**
- Konflikt in Migrationen, fehlende Migration, Schema-Inkonsistenz

**Recovery:**
1. Migrationen prüfen (`alembic history`)
2. Konflikte manuell auflösen (ggf. Migrationen zurücksetzen)
3. `alembic upgrade head` erneut ausführen

**Validierung:**
- Alembic Head stimmt, Backend startet

---

## 5. Backup beschädigt
**Symptom:**
- Restore schlägt fehl, Checksum-Fehler, Datei nicht lesbar

**Diagnose:**
- `validate_backup` meldet Fehler
- Checksum- oder Manifest-Fehler im Log

**Ursache:**
- Übertragungsfehler, unvollständiges Backup, Dateisystemfehler

**Recovery:**
1. Anderes (älteres) Backup verwenden
2. Backup-Integrität regelmäßig prüfen (`validate_backup`)

**Validierung:**
- Restore mit anderem Backup erfolgreich, Selftest PASS

---

## 6. Restore fehlgeschlagen
**Symptom:**
- Restore-Prozess bricht ab, Datenbank bleibt leer oder inkonsistent

**Diagnose:**
- Fehlermeldung im Restore-Log prüfen
- Datenbanktabellen prüfen (z.B. `SELECT COUNT(*) FROM documents;`)

**Ursache:**
- Backup defekt, falsche Restore-Parameter, DB nicht leer

**Recovery:**
1. Sicherstellen, dass DB leer ist (`operations_selftest.ps1` Check)
2. Restore erneut mit validem Backup durchführen
3. Logs auf Fehler prüfen

**Validierung:**
- Daten vorhanden, Selftest PASS

---

## 7. Reindex fehlgeschlagen
**Symptom:**
- Suche liefert keine oder falsche Ergebnisse, Reindex-Fehler im Log

**Diagnose:**
- Reindex-Log prüfen (`python -m app.scripts.reindex_full`)
- Index-Tabellen prüfen

**Ursache:**
- Fehlerhafte Daten, fehlende Abhängigkeiten, DB-Inkonsistenz

**Recovery:**
1. Reindex erneut ausführen
2. Bei Fehler: Restore und Reindex wiederholen

**Validierung:**
- Suche funktioniert, Selftest PASS

---

## 8. API nicht erreichbar
**Symptom:**
- Backend-Endpoints liefern keine Antwort, HTTP 5xx/4xx

**Diagnose:**
- `curl http://localhost:8000/health` schlägt fehl
- Backend-Logs prüfen

**Ursache:**
- Backend nicht gestartet, Port blockiert, Fehlerhafte Konfiguration

**Recovery:**
1. Backend-Logs analysieren
2. Backend neu starten
3. Ports und Umgebungsvariablen prüfen

**Validierung:**
- /health liefert Status ok

---

## 9. Frontend nicht erreichbar
**Symptom:**
- Weboberfläche lädt nicht, Browser-Fehler

**Diagnose:**
- `curl http://localhost:5173` schlägt fehl
- Browser-Konsole und Frontend-Logs prüfen

**Ursache:**
- Frontend nicht gebaut/gestartet, Port blockiert, Build-Fehler

**Recovery:**
1. Frontend Build prüfen (`npm run build`)
2. Frontend starten (`npm run dev` oder `npm run start`)
3. Ports prüfen

**Validierung:**
- Frontend im Browser erreichbar

---

## 10. Login nicht möglich
**Symptom:**
- Login-Formular zeigt Fehler, Authentifizierung schlägt fehl

**Diagnose:**
- Backend-/API-Logs prüfen
- Seed User prüfen

**Ursache:**
- Seed User fehlt, Passwort falsch, Auth-Service gestört

**Recovery:**
1. Seed User prüfen/wiederherstellen
2. Passwort zurücksetzen (Seed-Skript)
3. Backend neu starten

**Validierung:**
- Login erfolgreich, Selftest PASS

---

> **Hinweis:** Nach jeder Recovery-Maßnahme sollte das Selftest-Skript (`operations_selftest.ps1`) ausgeführt werden, um die Systemintegrität zu validieren.
