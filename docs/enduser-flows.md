# Enduser-Flows (RC-Stand)

Stand: 2026-06-15
Quelle: `reports/current/enduser_acceptance_rc.json`
Verdict: **BLOCKED** (S04 und S08 geblockt)

---

## S01 — Login

**Status: PASS**

1. Browser oeffnen: `http://localhost:5173`
2. Weiterleitung auf `/login`
3. Credentials eingeben (SEED_ADMIN_LOGIN / SEED_ADMIN_PASSWORD)
4. Bestaetigen → Redirect auf `/dashboard`

Fehlverhalten: Falsche Credentials → Fehlermeldung, kein Redirect.

---

## S02 — Dashboard aufrufen

**Status: PASS**

Nach Login: Dashboard zeigt Systemstatus-Felder (Release Status, System Health, Governance Gate, Security Gate, GUI Gate, RAG Status, Agent Status).

Datenbasis: `/api/v1/status`

---

## S03 — Dokument importieren

**Status: PASS (mit Warnung)**

Navigation: "Import" in der Sidebar → `/import`

Warnung: `/import` ist nicht im Masterplan final_navigation.md. Route funktional. Masterplan-Synchronisation ausstehend (NAV-FIX-03).

---

## S04 — Dokumente suchen

**Status: BLOCKED**

Die Sidebar-Verlinkung zeigt auf `/search` (SearchPage). Der Masterplan definiert Suche als `/chat` (ChatPage) — zwei verschiedene Komponenten mit unterschiedlichen Funktionen. Unklar welche als Release-Suche gilt.

Blockierender Befund: NAV-FIX-01 nicht geloest.

Workaround: Beide Routen per direktem URL erreichbar (`/search`, `/chat`).

---

## S05 — Themen-Uebersicht

**Status: PASS (mit Warnung)**

Navigation: "Themen" in der Sidebar → `/topics`

Warnung: `/topics` ist nicht im Masterplan. Masterplan-Synchronisation ausstehend (NAV-FIX-03).

---

## S06 — Datenanalyse aufrufen

**Status: PASS**

Navigation: "Datenanalyse" → `/rag`

Zeigt Dokument-Liste, Retrieve-Funktion verfuegbar.
Backend-Endpunkte: `/api/v1/rag/documents`, `/api/v1/rag/retrieve`

---

## S07 — Analyse-Ergebnis ansehen

**Status: PASS**

Im Datenanalyse-Bereich: Retrieve-Anfrage abschicken → Ergebnis wird angezeigt.

---

## S08 — Data Quality aufrufen (Read-Only)

**Status: BLOCKED**

Route `/data-quality` ist in `routes.jsx` vorhanden, fehlt aber in AppShell NAV_ITEMS. User kann Data Quality nicht per Navigationsklick aufrufen.

Workaround: Direkter URL-Aufruf `http://localhost:5173/data-quality`

Blockierender Befund: NAV-FIX-02 nicht geloest.

Data Quality ist read-only: nur GET-Operationen in `dataQuality.js`.

---

## S09 — Drift Detection aufrufen (Read-Only)

**Status: PASS**

Navigation: "Drift" in der Sidebar → `/drift` → DriftDashboard

Zeigt: LastRun, Severity-Verteilung, Type-Verteilung, Findings-Tabelle.
Keine Mutations-Aktionen moeglich (PROHIBIT-02, PROHIBIT-06 eingehalten).

Hinweis: Drift-Daten (drift_report.json, drift_summary.json) nur vorhanden wenn Drift CLI ausgefuehrt wurde.

---

## S10 — Logout

**Status: PASS**

Sidebar unten: "Abmelden" klicken → signOut() → Redirect auf `/login`.

---

## Zusammenfassung

| Szenario | Status |
|----------|--------|
| S01 Login | PASS |
| S02 Dashboard | PASS |
| S03 Import | PASS (Warnung) |
| S04 Suche | **BLOCKED** |
| S05 Themen | PASS (Warnung) |
| S06 Datenanalyse | PASS |
| S07 Analyse-Ergebnis | PASS |
| S08 Data Quality | **BLOCKED** |
| S09 Drift (read-only) | PASS |
| S10 Logout | PASS |

PASS: 7/10 | BLOCKED: 2/10 | PASS mit Warnung: 2/10
