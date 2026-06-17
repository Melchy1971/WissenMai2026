# RC Limitations — Stand PRI-6

Stand: 2026-06-17
Basis: warning_disposition_report.json, rc_stabilization_gate.json

Alle nachfolgenden Limitationen sind bekannt, dokumentiert und **nicht RC-blockend**. GA-Tickets sind angelegt.

---

## RCL-SEC-01 — Security Hardening: CSP/Secure-Headers

**Betrifft:** Backend HTTP-Response-Headers
**Status:** WARNING (SH-06-W1)
**RC-Impact:** keiner — Internal-Only Deployment im RC-Scope
**Workaround:** Kein öffentlicher Zugang. Deployment im internen Netzwerk.
**GA-Ticket:** GA-SEC-01 (Prio HOCH)
**Fix:** SecurityHeadersMiddleware in FastAPI — Aufwand 0.5 Tag

---

## RCL-EXP-01 — PDF-Export: Dry-Run-Simulation

**Betrifft:** Export Center — GP-07
**Status:** GP-07 PASS mit JSON/MD. PDF ist Dry-Run (3200ms simuliert).
**RC-Impact:** keiner — JSON/MD-Export vollständig und exportierbar
**Workaround:** JSON- und Markdown-Export als Primärformat. PDF optional.
**GA-Ticket:** GA-FUNC-02 (Prio MITTEL) — PO-Entscheidung oder WeasyPrint-Integration
**Constraint:** Nur APPROVED Results exportierbar — eingehalten.

---

## RCL-PERF-01 — Frontend-Bundle-Größe nicht gemessen

**Betrifft:** Frontend Build
**Status:** Frontend-Load p95=326ms — weit unter RC-Limit 3000ms
**RC-Impact:** keiner — p95 gemessen, Limit eingehalten
**Workaround:** Messung zeigt unkritische Werte. Kein LCP-Problem im RC-Scope.
**GA-Ticket:** GA-PERF-03 (Prio NIEDRIG) — vite-bundle-analyzer

---

## RCL-OPS-01 — DB Connection-Pool ohne Limit

**Betrifft:** Backend SQLAlchemy Session-Konfiguration
**Status:** Kein Pool-Limit gesetzt
**RC-Impact:** keiner — RC-Deployment < 5 parallele User, kein Ressourcenproblem
**Workaround:** SQLALCHEMY_POOL_SIZE in .env.example konfigurierbar (dokumentiert)
**GA-Ticket:** GA-OPS-01 (Prio NIEDRIG) — < 1h Fix

---

## Externe Blocker (kein Code-Fix möglich)

Diese Punkte blockieren **RC_READY**, nicht CONDITIONAL_RC:

| ID | Beschreibung | Verantwortung |
|----|-------------|---------------|
| SCGB-01 | TEST_DATABASE_URL in CI nicht gesetzt | DevOps |
| SCGB-02 | NAV_ITEMS PO-Entscheidung (Option A vs. B) | Product Owner |

Nach Auflösung beider Punkte: `rc_stabilization_gate` neu ausführen → RC_READY erreichbar.
