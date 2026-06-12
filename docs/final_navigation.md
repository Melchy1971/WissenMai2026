# Finale Navigation

**Datum:** 2026-06-12
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

## Drift Detection (vorgemerkt, nicht aktiv)

Sobald `reports/current/m5b_production_readiness_gate.json` = PASS:

| Label | Route | Komponente |
|-------|-------|-----------|
| Drift Detection | /drift | DriftDashboard (neu zu erstellen) |

Einfügen zwischen "Data Quality" und "Einstellungen". Gate-Bedingung: M5b Production Readiness PASS.

