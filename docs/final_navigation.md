# Finale Navigation

**Datum:** 2026-06-15 (aktualisiert)
**Quelle:** frontend/src/app/AppShell.jsx + frontend/src/app/routes.jsx

---

## Menüstruktur

| Label | Route | Komponente | Rollenbezug |
|-------|-------|-----------|------------|
| Dashboard | /dashboard | DashboardPage | alle authentifizierten Nutzer |
| Suche | /chat | ChatPage | alle authentifizierten Nutzer |
| Dokumente | /documents | DocumentsPage | alle authentifizierten Nutzer |
| Datenanalyse | /rag | RAGCenterPage | alle authentifizierten Nutzer |
| Data Quality | /data-quality | DataQualityPage | alle authentifizierten Nutzer |
| Einstellungen | /settings | SettingsPage | alle authentifizierten Nutzer |

---

## Untermenüs

| Übergeordnet | Sub-Route | Komponente |
|-------------|----------|-----------|
| Suche | /chat/:id | ChatPage (Session-Detail) |
| Dokumente | /documents/:id | DocumentDetailPage |

---

## Nicht in Navigation (aber Route vorhanden)

| Route | Komponente | Grund |
|-------|-----------|-------|
| /login | LoginPage | Auth-only, kein Nav-Item |

---

## Drift Detection (aktiv — formale Freigabe ausstehend)

Route und Komponente sind implementiert und erreichbar. Formale Freigabe blockiert durch m5b_production_readiness_gate BLOCKED.

| Label | Route | Komponente | Status |
|-------|-------|-----------|--------|
| Drift | /drift | DriftPage → drift_v2/DriftDashboard | Aktiv (Read-Only) |

Position: zwischen "Data Quality" und "Einstellungen".
Nachweis: `reports/current/drift_route_recovery_report.json` PASS, `reports/current/drift_v2_ui_truth_report.json` PASS (29/29).
Formale Freigabe: `reports/current/m5b_production_readiness_gate.json` BLOCKED — Gate-Kaskade aus M5a, root: TEST_DATABASE_URL.

**Cleanup/Repair in Drift: NO_GO** — PROHIBIT-02 (kein RepairButton), PROHIBIT-06 (kein CleanupButton). Drift Dashboard ist Read-Only ohne Ausnahme.

