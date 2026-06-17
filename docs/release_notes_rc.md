# Release Notes — Ruflo RC (CONDITIONAL_RC)

Version: 1.0-RC
Stand: 2026-06-17
Sprint: PRI-6 (Release Candidate Hardening)

---

## 1. Release Status

**CONDITIONAL_RC** — Freigabe für kontrollierten RC-Betrieb im internen Netzwerk.

Vollständige RC-Freigabe (RC_READY) steht aus bis:
1. `TEST_DATABASE_URL` in CI gesetzt (DevOps)
2. NAV_ITEMS PO-Entscheidung getroffen (Product Owner)

GA-Freigabe erfordert zusätzlich die Abarbeitung von GA-SEC-01, GA-PERF-01, GA-PERF-02.

---

## 2. Implementierte Hauptfunktionen

**Dokumentenzentrum (GP-02)**
Import von PDF-, DOCX- und Textdateien. Lifecycle-Status (active/archived/deleted). Keine technischen IDs im UI.

**Volltextsuche (GP-03)**
PostgreSQL FTS mit deutscher Sprachunterstützung. Ergebnisliste ohne UUIDs. Keine KWIC-Highlighting (GA-FUNC-01).

**Themenmanagement (GP-04)**
Topics mit Statusworkflow draft → review → approved → archived. Slug als URL-Parameter, keine UUID in URLs.

**Wissensanalyse (GP-05)**
10 API-Endpunkte. Analyse-Jobs mit Status-Polling. Ergebnis-Panel mit Topics und Quellen.

**Freigabe-Workflow (GP-06)**
Member → 403 bei Approve-Endpunkt. Admin → Confirmation-Dialog. Import nur mit `confirm=true` + `actor_role=admin`. PROHIBIT-08 eingehalten.

**Export Center (GP-07)**
JSON- und Markdown-Export vollständig. Quellen immer eingeschlossen. Nur APPROVED Results exportierbar. PDF-Export: Dry-Run (siehe Limitationen).

**Dashboard Drift Analytics (GP-08)**
6 Drift-Karten, GlobalStatusBar, AppShell-Badge, Klick → DriftDetail, History-Chart.

---

## 3. Gold Path Ergebnis

| GP | Schritt | Status |
|----|---------|--------|
| GP-01 | Login / Bereichsauswahl | PASS |
| GP-02 | Dokument importieren | PASS |
| GP-03 | Dokument suchen | PASS |
| GP-04 | Themen finden und bearbeiten | PASS |
| GP-05 | Analyse starten und Ergebnis anzeigen | PASS |
| GP-06 | Analyse freigeben und übernehmen | PASS |
| GP-07 | Export erzeugen | PASS |
| GP-08 | Dashboard Status prüfen | PASS |

**Ergebnis: 8/8 PASS** — RC_READY-Kriterium für Gold Path erfüllt.

---

## 4. Security Status

| Bereich | Status | Bemerkung |
|---------|--------|-----------|
| SH-01 Secret Handling | PASS | Keine Klartextpasswörter, kein committed .env |
| SH-02 Privacy Mode | PASS | SECRET-Dokumente in RAG gesperrt |
| SH-03 Data Classification | PASS | PUBLIC/INTERNAL/CONFIDENTIAL/SECRET |
| SH-04 Audit Logging | PASS | Immutable Events, keine SECRET-Einträge sichtbar |
| SH-05 Access Control | PASS | AdminRoute-Guard (PRI-6), PROHIBIT-08, Workspace-Isolation |
| SH-06 Input Validation / Secure Headers | WARNING | CSP nicht gesetzt — GA-SEC-01 |

**Technical ID Leak Gate (GATE-18):** 0 Leaks in 72 Frontend-Dateien. CI-blockend.

---

## 5. Bekannte Limitationen

| ID | Beschreibung | Workaround |
|----|-------------|------------|
| RCL-SEC-01 | CSP/Secure-Headers fehlen | Internal-Only Deployment |
| RCL-EXP-01 | PDF-Export: Dry-Run-Simulation | JSON/MD-Export als Primärformat |
| RCL-PERF-01 | Frontend-Bundle-Größe nicht gemessen | p95=326ms weit unter RC-Limit |
| RCL-OPS-01 | Kein DB Connection-Pool-Limit | RC-Deployment < 5 parallele User |

---

## 6. Workarounds

**Suche ohne Highlighting:** Ergebnisliste zeigt Dokumenttitel. Direkte Navigation zum Dokument über Klick möglich.

**PDF-Export:** JSON- oder Markdown-Export verwenden. Datei enthält alle Analyseergebnisse und Quellen.

**Dashboard W06 Drift-Widget fehlt:** Direkte Navigation zu `/drift-analytics` für vollständige Drift-Übersicht.

**NAV_ITEMS-Entscheidung offen:** Aktuelle Navigation vollständig funktional. Endgültige Struktur nach PO-Entscheidung.

---

## 7. Nicht enthaltene GA-Funktionen

Die folgenden Features sind im GA-Backlog, aber nicht im RC-Scope:

- KWIC-Trefferhighlighting und Stemming (GA-FUNC-01)
- Dashboard Drift-Summary-Widget W06 (GA-UX-01)
- Echter PDF-Renderer (GA-FUNC-02)
- GIN-Index für Suchperformanz unter Last (GA-PERF-01)
- SQL-seitiges Sorting (GA-PERF-02)
- CSP/Secure-Headers (GA-SEC-01)

---

## 8. Teststatus

| Testart | Umfang | Status |
|---------|--------|--------|
| API Contract Tests | 85/85 | PASS |
| E2E Gold Path Tests | 54 Tests, 8 Flows | PASS |
| Technical ID Leak Gate | 27 Tests (19 Unit + 8 E2E) | PASS |
| AdminRoute Guard Tests | 3 Tests | PASS |
| Security Rules E2E | Member→403, PROHIBIT-08 | PASS |
| Error Flows | 7 Szenarien | PASS |

**TEST_DATABASE_URL:** Nicht in CI gesetzt → Backup/Restore-Retest und Performance-Smoke ausstehend (SCGB-01).

---

## 9. Betriebsanforderungen

**Umgebungsvariablen (Pflicht):**
```
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
SECRET_KEY=<zufälliger 32-Byte-Wert>
ADMIN_API_TOKEN=<sicherer Token>
```

**Empfohlen:**
```
MAX_UPLOAD_SIZE_BYTES=52428800
ORIGINAL_FILE_STORE_DIR=/var/ruflo/files
BACKUP_RESTORE_ROOT_DIR=/var/ruflo/restore
BACKGROUND_JOB_LOCK_TIMEOUT_SECONDS=300
```

Vollständige Liste: `.env.example`

**Migrations:** `alembic upgrade head` vor erstem Start.

**Health-Endpunkte:**
- `GET /health` — Backend-Status
- `GET /health/db` — Datenbankverbindung

**Ops-Dokumentation:** `docs/operations/` (Runbook, Backup/Restore, Troubleshooting, Healthchecks)

---

## 10. Upgrade-/Migrationshinweise

Erstinstallation — kein Upgrade-Pfad erforderlich.

Für Deployments aus Entwicklungsstand:
1. `alembic upgrade head` ausführen
2. `.env` gegen `.env.example` abgleichen — neue Variablen: `ADMIN_API_TOKEN`, `MAX_UPLOAD_SIZE_BYTES`, alle `BACKGROUND_JOB_*`
3. Frontend-Build: `npm run build`
4. `GET /health/db` prüfen — muss `{"status": "ok"}` zurückgeben
5. Gold Path GP-01 manuell durchlaufen

**Rollback:** Alembic-Downgrade auf vorherige Revision. Datenbank-Dump vor Migration empfohlen (siehe `docs/operations/backup_restore.md`).
