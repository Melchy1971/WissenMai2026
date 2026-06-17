# GA Test Matrix — PRI-7

Stand: 2026-06-17
Quelle: `reports/current/ga_regression_report.json`

---

## Status-Legende

| Symbol | Bedeutung |
|--------|-----------|
| PASS | Implementiert und bestanden |
| TEIL | Teilweise vorhanden |
| SPEC | Spezifiziert, nicht implementiert |
| GESPERRT | SCGB-01 (TEST_DATABASE_URL) |
| — | Nicht anwendbar |

---

## Test-Matrix

| Bereich | Unit | Integration | Contract | E2E | Performance | Security | A11y |
|---------|------|-------------|---------|-----|-------------|----------|------|
| Documents | TEIL | GESPERRT | — | SPEC | SPEC | SPEC | — |
| Search | TEIL | GESPERRT | — | SPEC | SPEC | SPEC | — |
| Topics | TEIL | GESPERRT | — | SPEC | — | — | — |
| Analysis | TEIL | GESPERRT | SPEC | SPEC | — | — | — |
| Approval | PASS | GESPERRT | — | SPEC | — | PASS | — |
| Export | TEIL | GESPERRT | — | SPEC | SPEC | PASS | — |
| Dashboard | TEIL | GESPERRT | — | SPEC | SPEC | — | — |
| Drift | PASS | GESPERRT | — | SPEC | — | — | — |
| Reports | TEIL | — | — | — | — | PASS | — |
| Jobs | TEIL | GESPERRT | — | — | — | — | — |

---

## Gesperrte Tests (SCGB-01)

Alle Integrations-Tests benötigen `TEST_DATABASE_URL`. Dieser Environment-Variable ist von DevOps bereitzustellen (SCGB-01).

Betroffen: Documents, Search, Topics, Analysis, Export, Dashboard, Drift, Jobs — Integration-Spalte.

---

## Security-Tests (implementiert)

- Approval: DRAFT zeigt Freigabe-Hinweis ✅
- Approval: nur APPROVED exportierbar ✅
- Approval: keine technischen IDs in UI ✅
- Export: workspace_id Scope ✅
- Reports: Snapshots immutable ✅
- Reports: alte Snapshots erhalten ✅
- Admin: AdminRoute-Guard /admin/diagnostics ✅

---

## Performance-Ziele (spezifiziert)

| Bereich | Ziel | Status |
|---------|------|--------|
| Upload 10 MB | < 5s | SPEC |
| Suche (10k Chunks) | < 500ms | SPEC |
| PDF-Export | < 10s | SPEC |
| Dashboard-Load | < 1s | SPEC |

---

## GA-Blocking

**Integrations-Tests: GESPERRT** — GA_READY nicht erreichbar ohne SCGB-01.

**Unit-Test-Coverage: TEILWEISE** — Gaps in Sonderzeichen-Handling, Edge-Cases, Job-Framework.
