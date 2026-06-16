# Release Candidate

Stand: 2026-06-15
Entscheidung: **BLOCKED**
Quelle: `reports/current/release_candidate_gate.json`

RC-Gate: 2/7 Bedingungen erfuellt (GATE-06 Cleanup NO-GO, GATE-07 0 BLOCKING_CORE).

---

## Installation

### Voraussetzungen

- Python 3.11+
- Node.js 20+
- PostgreSQL (remote, z.B. `85.215.131.200:5432/wissen2026`)
- PowerShell (Windows) oder bash (Linux/macOS)

### Backend

```powershell
Set-Location H:\WissenMai2026

# Umgebungsvariablen (.env, nie committen)
# DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
# TEST_DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname  ← für Gate-Tests erforderlich
# APP_ENV=local
# DEFAULT_WORKSPACE_ID=...
# DEFAULT_USER_ID=...
# SEED_ADMIN_LOGIN=admin@localhost
# SEED_ADMIN_PASSWORD=change-me

# Vollständiger Bootstrap (DB + Migrationen + Seed + Smoke)
.\scripts\dev_bootstrap.ps1

# Oder manuell:
.\scripts\dev-db.ps1
.\scripts\dev-backend.ps1
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Start

```powershell
# Backend (FastAPI auf Port 8000)
.\scripts\dev-backend.ps1

# Frontend (Vite auf Port 5173)
.\scripts\dev-frontend.ps1
```

API: `http://localhost:8000`
Frontend: `http://localhost:5173`
Health-Check: `http://localhost:8000/health`

---

## Login / Seed

Seed wird automatisch beim Bootstrap angelegt.

```
Login: admin@localhost   (SEED_ADMIN_LOGIN)
Passwort: change-me      (SEED_ADMIN_PASSWORD)
```

Produktive Credentials über `.env` setzen. Niemals `.env` committen.

Auth Bootstrap prüfen:

```powershell
python scripts/check_auth_bootstrap.py --no-start-api
```

---

## Bekannte Einschränkungen

Vollständige Liste: `reports/current/known_limitations.json`, `docs/known_limitations.md`

| ID | Severity | Beschreibung |
|----|----------|-------------|
| KL-M5-T-001 | high | M5 Entropy-/Drift-Truth-Failures blockieren Slice-Start |
| KL-M5-T-002 | high | Drei Pflicht-Artefakte pro M5-Slice fehlen vor Slice-Start |
| KL-GOV-001 | high | Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt |
| KL-DEF-001 | low | OCR für gescannte PDFs nicht Teil von V1 |
| KL-DEF-002 | low | Embeddings und Vektorsuche optional, nicht V1-kritisch |
| KL-NB-001 | low | API-Alias /api/v1/documents nicht durchgängig verfügbar |

Keine Limitation mit `BLOCKING_CORE` severity — Voraussetzung für RC teilweise erfüllt.

---

## Release Candidate Gate

**Entscheidung: BLOCKED** (reports/current/release_candidate_gate.json)

| Gate | Bedingung | Status |
|------|-----------|--------|
| GATE-01 | local_final_gate PASS | BLOCKED |
| GATE-02 | Enduser Acceptance PASS | BLOCKED |
| GATE-03 | Security Smoke PASS | BLOCKED |
| GATE-04 | Navigation Release Check PASS | BLOCKED |
| GATE-05 | Report Integrity Final PASS | BLOCKED |
| GATE-06 | 0 BLOCKING_CORE Limitations | PASS |
| GATE-07 | Cleanup/Repair NO-GO bestaetigt | PASS |

**Root causes:**

1. `TEST_DATABASE_URL` nicht gesetzt: pytest 0 collected -> report_integrity_v2 BLOCKED (20 Blocker) -> final_gate_report BLOCKED
2. AppShell NAV_ITEMS divergiert vom Masterplan: /search statt /chat, /data-quality fehlt, /topics + /import extra
3. routes.jsx: /admin/diagnostics ohne Router-seitigen Admin-Guard; 7 undokumentierte Routen ohne Rollentrennung

**Mindest-Fixes vor RC:**

- RC-PREREQ-01: TEST_DATABASE_URL setzen, pytest + report_integrity_v2 regenerieren
- RC-PREREQ-02: AppShell NAV_ITEMS mit Masterplan synchronisieren (4 Abweichungen)
- RC-PREREQ-03: routes.jsx Admin-Guard und verbotene Routen bereinigen

---

## External Env Gate

Status: `NOT_RUN` — Quelle: `reports/current/external_env_gate.json`

72 Tests in 6 Dateien verwenden `httpx` gegen `localhost:8000`. Lokal ohne aktiven Server nicht ausführbar.

Blockiert `local_final_gate` **nicht**. Blockiert Release Candidate **nicht** (NOT_RUN ist erlaubter Zustand).

Ausführung (Server muss laufen + TEST_DATABASE_URL gesetzt):

```bash
pytest tests/api -m "external_env_only or legacy_live_http"
```

Test-Dateien:
- `tests/api/test_gui_backend_endpoints.py`
- `tests/api/test_gui_contracts.py`
- `tests/api/test_gui_secret_masking.py`
- `tests/api/test_secret_masking_api.py`
- `tests/api/test_settings_endpoints.py`
- `tests/api/test_settings_patch.py`

---

## Cleanup / Repair: NO-GO

**M5c Cleanup ist gesperrt.** Bedingungen für GO nicht erfüllt:
1. `reports/current/m5c_start_gate.json` ≠ PASS (aktuell BLOCKED)
2. PO-Sign-off auf `reports/current/cleanup_governance_boundary.json` nicht erteilt

Aktive Verbote:
- **PROHIBIT-02**: Kein RepairButton in DriftDashboard oder anderen Komponenten
- **PROHIBIT-06**: Kein CleanupButton in DriftDashboard oder anderen Komponenten
- **PROHIBIT-08**: Keine automatische M5c-Ausführung ohne PO-Approval je Proposal

Drift Detection ist **Read-Only**. Kein Schreiben, kein Reparieren, kein Bereinigen.

---

## Gate-Reports

| Report | Status | Zweck |
|--------|--------|-------|
| `reports/current/release_candidate_gate.json` | BLOCKED | Finales RC Gate (7 Bedingungen) |
| `reports/current/final_gate_report.json` | BLOCKED | Local Final Gate (Validator v2) |
| `reports/current/enduser_acceptance_rc.json` | BLOCKED | Enduser Acceptance (7/10 PASS) |
| `reports/current/rc_security_smoke_report.json` | BLOCKED | Security Smoke (9/10 PASS) |
| `reports/current/final_navigation_release_check.json` | BLOCKED | Navigation vs. Masterplan (4/8 PASS) |
| `reports/current/rc_report_integrity_final.json` | BLOCKED | Report Integrity Final |
| `reports/current/external_env_gate.json` | NOT_RUN | Externe Tests (nicht blockierend) |
| `reports/current/release_candidate_decision.json` | BLOCKED | RC-Entscheidung (Vorgaenger-Report) |
| `reports/current/report_integrity_v2.json` | BLOCKED | Report-Konsistenz (20 Blocker) |
| `reports/current/documentation_truth_lint.json` | PASS | Dokumentations-Lint (19/19) |
| `reports/current/drift_v2_permission_guard_report.json` | PASS | Drift v2 Regression Guard (6/6) |
| `reports/current/known_limitations.json` | INFO | Bekannte Einschraenkungen (0 BLOCKING_CORE) |
