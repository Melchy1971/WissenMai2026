# Finale Navigation (RC-Stand)

Stand: 2026-06-15
Quelle: `reports/current/final_navigation_release_check.json`
Verdict: **BLOCKED** (Abweichungen zwischen AppShell und Masterplan)

---

## Ziel-Menuestruktur (Masterplan)

Quelle: `docs/final_navigation.md` (Masterplan-Referenz)

| Label | Route | Komponente |
|-------|-------|-----------|
| Dashboard | /dashboard | DashboardPage |
| Suche | /chat | ChatPage |
| Dokumente | /documents | DocumentCenterPage |
| Datenanalyse | /rag | RAGCenterPage |
| Data Quality | /data-quality | DataQualityPage |
| Einstellungen | /settings | SettingsPage |

Drift Detection: implementiert, Read-Only, formale Freigabe ausstehend (m5b_production_readiness BLOCKED).

---

## Ist-Zustand (AppShell NAV_ITEMS)

| Label | Route | Status |
|-------|-------|--------|
| Dashboard | /dashboard | OK |
| Dokumente | /documents | OK |
| Themen | /topics | EXTRA (nicht im Masterplan) |
| Import | /import | EXTRA (nicht im Masterplan) |
| Suche | /search | ABWEICHUNG (Masterplan: /chat) |
| Datenanalyse | /rag | OK |
| Drift | /drift | OK (Read-Only) |
| Einstellungen | /settings | OK |
| Data Quality | (fehlt) | MISSING (Masterplan: /data-quality) |

---

## Offene Abweichungen (NAV-FIX)

| Fix-ID | Prioritaet | Aktion |
|--------|-----------|--------|
| NAV-FIX-01 | 1 | /search durch /chat ersetzen oder Masterplan anpassen |
| NAV-FIX-02 | 1 | /data-quality in NAV_ITEMS aufnehmen |
| NAV-FIX-03 | 2 | /topics und /import entfernen oder Masterplan aktualisieren |
| NAV-FIX-04 | 2 | /tools /memory /tasks /projects /agents /collaboration /governance aus routes.jsx entfernen oder Admin-Guard |
| NAV-FIX-05 | 3 | AdminRoute-Wrapper fuer /admin/diagnostics auf Router-Ebene |

---

## Zugangsschutz

Alle Routen (ausser /login) sind hinter `ProtectedRoute` (Authentifizierung erforderlich).
`/admin/diagnostics`: Komponenten-seitiger isAdmin()-Check vorhanden, aber kein Router-seitiger Admin-Guard.

---

## Drift Detection (Read-Only)

Route: `/drift` → DriftPage → `drift_v2/DriftDashboard`

Aktiv und erreichbar. Ausschliesslich lesender Zugriff.
- PROHIBIT-02: kein Repair-Button
- PROHIBIT-06: kein Cleanup-Button
- PROHIBIT-08: keine Auto-Execution

DriftV2RegressionGuard: 6/6 PASS (`reports/current/drift_v2_permission_guard_report.json`)

---

## Data Quality (Read-Only)

Route: `/data-quality` → DataQualityPage → DataQualityDashboard

Vorhanden in routes.jsx, nicht in AppShell NAV_ITEMS (NAV-FIX-02).
Nur GET-Operationen in `dataQuality.js`.
