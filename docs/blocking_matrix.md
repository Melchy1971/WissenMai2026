# Blocking Matrix — PRI-6

Stand: 2026-06-17
Basis: rc_final_gate_report, rc_stabilization_gate, security_hardening_report, performance_baseline_report, product_gold_path

---

## Schwergrade

| Grad | Bedeutung |
|------|-----------|
| CRITICAL | Blockiert RC-Freigabe oder verletzt Security-Constraint |
| HIGH | Blockiert GA oder erzeugt messbaren User-Impact |
| MEDIUM | Qualitätsrisiko, kein akuter RC-Blocker |
| LOW | Dokumentiertes Risiko, kein messbarer Impact im RC-Scope |

---

## Priorisierte Blocker-Matrix

| # | ID | Quelle | Grad | GP | Komponente | Fix-Aufwand | Scope |
|---|-----|--------|------|----|------------|-------------|-------|
| 1 | BLK-01 | SCGB-03 | **CRITICAL** | GP-01 | routes.jsx /admin/diagnostics | < 2h | Code — PRI-6 |
| 2 | BLK-02 | SCGB-01 | **CRITICAL** | — | CI TEST_DATABASE_URL | 0.5–1 Tag DevOps | Extern |
| 3 | BLK-03 | SCGB-02 | HIGH | GP-01 | NAV_ITEMS | PO-Entscheidung | Extern |
| 4 | BLK-04 | SH-06-W1 | HIGH | — | FastAPI HTTP-Headers | 0.5 Tag | GA |
| 5 | BLK-05 | RISIKO-01 | MEDIUM | GP-03 | ILIKE ohne GIN-Index | < 1h | GA |
| 6 | BLK-06 | RISIKO-02 | MEDIUM | GP-03 | search_unified Sorting | 1–2 Tage | GA |
| 7 | BLK-07 | RCL-02 | MEDIUM | GP-08 | Dashboard W06 Drift-Widget | 1–2 Tage | GA |
| 8 | BLK-08 | RCL-01 | LOW | GP-07 | PDF-Export | PO oder 2–3 Tage | GA |
| 9 | BLK-09 | RISIKO-04 | LOW | — | Bundle-Größe | 0.5 Tag | GA |
| 10 | BLK-10 | RISIKO-05 | LOW | — | DB Connection Pool | < 1h | GA |

---

## BLK-01 — SCGB-03 Router-Guard (CRITICAL, Code-fixable)

**Ursache:** `AdminDiagnosticsPage` ist innerhalb `ProtectedRoute` (Token-Check), aber ohne Role-Check. Jeder authentifizierte User kann `/admin/diagnostics` aufrufen.

**Impact:** Member-User sehen Diagnose-Daten (System-Status, DB-Verbindungen, Job-Queues). Verletzt SH-05.

**Fix:** `AdminRoute`-Komponente in `routes.jsx` — `auth.user.role === 'admin'`, sonst 403.

**Risiko bei Nichtbehebung:** Security-FAIL bei GA. SCG-05 bleibt PARTIAL_PASS.

---

## BLK-02 — SCGB-01 TEST_DATABASE_URL (CRITICAL, Extern)

**Ursache:** `TEST_DATABASE_URL` in CI nicht gesetzt. Backup/Restore-Retest, report_integrity_v2 und Performance-Smoke schlagen fehl.

**Fix:** PostgreSQL-Container in CI-Pipeline oder TEST_DATABASE_URL auf Staging-DB konfigurieren (DevOps).

**Risiko bei Nichtbehebung:** `rc_stabilization_gate` bleibt BLOCKED. Kein RC_READY erreichbar.

---

## BLK-03 — SCGB-02 NAV_ITEMS (HIGH, PO-Entscheidung)

**Ursache:** Entscheidung Option A (5 Items) vs. Option B (8 Items) nicht getroffen.

**Fix:** PO trifft Entscheidung → 0.5 Tag Implementierung.

**Risiko bei Nichtbehebung:** GP-01 Navigation nicht abschließend verifiziert.

---

## BLK-04 — SH-06-W1 CSP / Secure Headers (HIGH, GA)

**Ursache:** HTTP-Security-Header fehlen. Kein Test vorhanden.

**Fix:** `SecurityHeadersMiddleware` in FastAPI + Header-Tests in Contract-Suite.

---

## BLK-05/06 — Performance (MEDIUM, GA)

- **BLK-05:** GIN-Index für ILIKE-Suche — Alembic-Migration < 1h
- **BLK-06:** SQL-seitiges Sorting in `search_unified` — 1–2 Tage

---

## BLK-07–10 — GA-Backlog (MEDIUM/LOW)

Alle in `ga_backlog.json` erfasst. Kein RC-Impact.

---

## PRI-6 Fix-Scope

In PRI-6 code-seitig behebbar: **BLK-01** (SCGB-03 Router-Guard).

BLK-02 und BLK-03 erfordern externe Aktionen (DevOps / PO). Sie bleiben als CONDITIONAL_RC-Blocker dokumentiert.
