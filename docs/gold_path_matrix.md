# Gold Path Matrix

Stand: 2026-06-17 | Quelle: `reports/current/product_gold_path.json`

## Übersicht

| GP | Name | Rolle | Status | Sicherheitskritisch | Blocking 1.0 |
|---|---|---|---|---|---|
| GP-01 | Login / Bereichsauswahl | Alle | PASS | Nein | Ja |
| GP-02 | Dokument importieren | Member, Admin | PASS | Nein | Ja |
| GP-03 | Dokument suchen | Alle | PASS | Nein | Ja |
| GP-04 | Themen finden und bearbeiten | Member, Admin | PASS | Nein | Ja |
| GP-05 | Analyse starten und Ergebnis anzeigen | Member, Admin | PASS | Nein | Ja |
| GP-06 | Analyse freigeben und übernehmen | Admin | PASS | **Ja** | Ja |
| GP-07 | Export erzeugen | Member, Admin | PASS | Nein | Ja |
| GP-08 | Dashboard Status prüfen | Alle | PASS | Nein | Ja |

**Gesamt: 8/8 PASS — Gate-Bewertung: RC_READY**

---

## GP-01 — Login / Bereichsauswahl

**Ziel:** Benutzer authentifiziert sich und wählt seinen Workspace aus.

**Nutzerrolle:** Alle Rollen

**Vorbedingungen:**
- Benutzer ist registriert
- Workspace existiert

**Schritte:**
1. Zu `/login` navigieren
2. E-Mail + Passwort eingeben, Login-Button klicken
3. Workspace-Auswahlseite erscheint bei mehreren Workspaces
4. Workspace auswählen → Weiterleitung zu `/dashboard`
5. Auth-Token im Header gesetzt, Workspace-ID im JWT

**Erwartetes Ergebnis:** Dashboard geladen, kein UUID sichtbar, Navigation vollständig, kein technischer Bezeichner als Primärtext.

**API-Abhängigkeiten:** `POST /api/v1/auth/login`, `GET /api/v1/workspaces`, `GET /api/v1/dashboard/summary`

**UI-Komponenten:** `LoginPage.jsx`, `WorkspaceSelectPage.jsx`, `AppShell.jsx`

**Testdateien:** `frontend/tests/gui_truth/test_navigation.spec.js`

**Status:** PASS | **Blocker:** Keine | **Risiko:** NIEDRIG

---

## GP-02 — Dokument importieren

**Ziel:** Dokument wird hochgeladen, verarbeitet und erscheint in der Dokumentenliste.

**Nutzerrolle:** Member, Admin

**Vorbedingungen:**
- Eingeloggt und Workspace ausgewählt

**Schritte:**
1. Zu `/documents` navigieren
2. Import-Button klicken → Upload-Dialog öffnet sich
3. PDF-Datei auswählen und hochladen
4. BackgroundJob startet, Status-Polling läuft (pending → running → completed)
5. Dokument erscheint in Liste mit Titel, ohne UUID

**Erwartetes Ergebnis:** Dokument importiert, `lifecycle_status=active`, kein UUID in der Listenansicht.

**API-Abhängigkeiten:** `POST /api/v1/documents/import`, `GET /api/v1/documents`, `GET /api/v1/background-jobs/:id`

**UI-Komponenten:** `DocumentsPage.jsx`, `ImportDialog.jsx`, `DocumentList.jsx`

**Testdateien:** `backend/tests/test_document_import.py`

**Status:** PASS | **Blocker:** Keine | **Risiko:** NIEDRIG

---

## GP-03 — Dokument suchen

**Ziel:** Benutzer findet Dokument über Volltextsuche mit KWIC-Highlighting.

**Nutzerrolle:** Alle Rollen

**Vorbedingungen:**
- Mindestens 1 Dokument importiert und indiziert

**Schritte:**
1. Suchfeld in `/documents` aktivieren
2. Suchbegriff eingeben (mindestens 3 Zeichen)
3. Suchergebnisse mit Treffer-Highlighting erscheinen
4. Dokument anklicken → `DocumentDetail`
5. Keine UUIDs in Suchergebnissen sichtbar

**Erwartetes Ergebnis:** Suchergebnisse mit KWIC-Highlighting, Klick öffnet Dokument-Detail korrekt.

**API-Abhängigkeiten:** `GET /api/v1/search?q=...`

**UI-Komponenten:** `DocumentsPage.jsx`, `SearchBar.jsx`, `SearchResults.jsx`

**Testdateien:** `backend/tests/test_search.py`

**Status:** PASS | **Blocker:** Keine | **Risiko:** NIEDRIG — PostgreSQL FTS ohne `TEST_DATABASE_URL` geskippt (bekannte Limitation)

---

## GP-04 — Themen finden und bearbeiten

**Ziel:** Benutzer sieht, bearbeitet und ändert den Status von Topics.

**Nutzerrolle:** Member, Admin

**Vorbedingungen:**
- Analyse-Ergebnisse vorhanden mit `suggested_topics`

**Schritte:**
1. Zu `/topics` navigieren
2. Themen-Liste laden (Status: draft, review, approved, archived)
3. Topic anklicken → `TopicDetail`
4. Metadaten bearbeiten (Name, Tags, Status)
5. Speichern → Status wechselt, kein UUID in URL oder Labels

**Erwartetes Ergebnis:** Topics bearbeitbar, Status-Wechsel persistiert, kein UUID als Primärtext.

**API-Abhängigkeiten:** `GET /api/v1/topics`, `PATCH /api/v1/topics/:id`, `GET /api/v1/topics/:id`

**UI-Komponenten:** `TopicsPage.jsx`, `TopicDetail.jsx`, `TopicStatusBadge.jsx`

**Testdateien:** `backend/tests/test_topics.py`

**Status:** PASS | **Blocker:** Keine | **Risiko:** NIEDRIG

---

## GP-05 — Analyse starten und Ergebnis anzeigen

**Ziel:** Analyse-Job wird gestartet und das Ergebnis angezeigt (status=draft, kein Auto-Approve).

**Nutzerrolle:** Member, Admin

**Vorbedingungen:**
- Mindestens 1 Dokument importiert

**Schritte:**
1. Zu `/analysis` navigieren
2. „Neue Analyse"-Button klicken → 5-Schritt-Wizard öffnet sich
3. Dokumente auswählen, Analyse-Typ wählen, starten
4. Job-Status-Anzeige: pending → running → completed
5. Ergebnis anklicken → `AnalysisResultPanel`: Zusammenfassung, Topics, Suggestions

**Erwartetes Ergebnis:** Analyse-Job abgeschlossen, Ergebnis status=draft (kein Auto-Approve), kein UUID als Primärtext.

**API-Abhängigkeiten:** `POST /api/v1/analysis/jobs`, `GET /api/v1/analysis/jobs/:id`, `GET /api/v1/analysis/results/:id`

**UI-Komponenten:** `AnalysisPage.jsx`, `NewAnalysisJobDialog.jsx`, `AnalysisJobList.jsx`, `AnalysisResultPanel.jsx`

**Testdateien:** `backend/tests/test_analysis_service.py`, `backend/tests/test_analysis_api_gold_path.py`

**Status:** PASS | **Blocker:** Keine | **Risiko:** MITTEL — LLM-Provider im Produktivbetrieb erfordert Konfiguration (bekannte Limitation)

---

## GP-06 — Analyse freigeben und Ergebnis übernehmen ⚠️ SICHERHEITSKRITISCH

**Ziel:** Admin gibt Analyse-Ergebnis frei und importiert Topics/Tags in die Wissensbasis.

**Nutzerrolle:** Admin (Member: Einreichen erlaubt, Freigabe nicht)

**Vorbedingungen:**
- Analyse-Ergebnis mit status=draft oder review vorhanden

**Schritte:**
1. Analyse-Ergebnis öffnen (status=draft)
2. „Zur Prüfung einreichen" klicken → status=review
3. Als Admin: „Freigeben" klicken → Confirmation-Dialog erscheint
4. Bestätigen → status=approved
5. „In Wissensbasis übernehmen" klicken → ImportDialog
6. confirm=true + admin-Rolle → Import ausgeführt; Topics landen in status=draft (kein Auto-Approve)

**Erwartetes Ergebnis:** status=approved, Topics/Tags importiert, kein Auto-Approve ohne Bestätigung (PROHIBIT-08).

**API-Abhängigkeiten:** `POST /api/v1/analysis/results/:id/review`, `POST /api/v1/analysis/results/:id/approve`, `POST /api/v1/analysis/results/:id/import`

**UI-Komponenten:** `AnalysisResultPanel.jsx`, `ApprovalButtons.jsx`, `ImportDialog.jsx`

**Testdateien:** `backend/tests/test_analysis_service.py`, `backend/tests/integration/test_analysis_gold_path.py`

**Status:** PASS | **Blocker:** Keine

**Sicherheitsregeln:**
- Member → 403 bei Approve-Endpunkt
- PROHIBIT-08: Import nur nach `confirm=true` + `actor_role=admin`
- Topics nach Import in status=draft (kein Auto-Approve)

**Risiko:** HOCH — Sicherheitskritisch. Ausfall blockiert RC auch wenn 7/8 andere Schritte PASS.

---

## GP-07 — Export erzeugen

**Ziel:** Freigegebenes Ergebnis wird als PDF, Markdown oder JSON exportiert und heruntergeladen.

**Nutzerrolle:** Member, Admin

**Vorbedingungen:**
- Analyse-Ergebnis status=approved ODER Topic vorhanden

**Schritte:**
1. Zu `/export` navigieren ODER ExportButton in Analyseergebnis klicken
2. Format auswählen (PDF, Markdown, JSON)
3. „Export starten" klicken → Job angelegt
4. Status-Anzeige: pending → running → completed
5. Download-Link erscheint, Datei herunterladen
6. Kontrolle: Draft-Status → kein ExportButton (Guard aktiv, Hinweis-Banner)

**Erwartetes Ergebnis:** Export enthält Inhalte + Quellen (immer eingeschlossen), keine UUIDs als Primärtext, keine Secrets in der Datei.

**API-Abhängigkeiten:** `POST /api/v1/export/jobs`, `GET /api/v1/export/jobs/:id`, `GET /api/v1/export/jobs/:id/download`, `GET /api/v1/export/templates`

**UI-Komponenten:** `ExportCenterPage.jsx`, `ExportJobList.jsx`, `ExportButton.jsx`

**Testdateien:** `backend/tests/test_export.py`, `reports/current/export_gold_path.json`

**Status:** PASS | **Blocker:** Keine | **Risiko:** NIEDRIG

---

## GP-08 — Dashboard Status prüfen

**Ziel:** Benutzer sieht den aktuellen Systemstatus und navigiert zu Drift Analytics.

**Nutzerrolle:** Alle Rollen

**Vorbedingungen:**
- Eingeloggt, Workspace mit Daten

**Schritte:**
1. Zu `/dashboard` navigieren
2. Summary-Widget: Dokument-Zahl, offene Analysen, Topics-Count sichtbar
3. DriftWidgetPanel: 6 Drift-Karten, GlobalStatusBar
4. Drift-Badge in AppShell-Statusbar sichtbar
5. Drift-Karte klicken → `/drift-analytics/:snapshotType`

**Erwartetes Ergebnis:** Dashboard zeigt aktuellen Status aller Bereiche, kein UUID sichtbar, Drift-Navigation funktioniert.

**API-Abhängigkeiten:** `GET /api/v1/dashboard/summary`, `GET /api/v1/dashboard/drift`, `GET /api/v1/drift/overview`

**UI-Komponenten:** `DashboardPage.jsx`, `DriftWidgetPanel.jsx`, `AppShell.jsx`, `DriftAnalyticsPage.jsx`

**Testdateien:** `reports/current/drift_gold_path.json`, `reports/current/drift_coverage.json`, `reports/current/dashboard_release_report.json`

**Status:** PASS | **Blocker:** Keine | **Risiko:** NIEDRIG

---

## Gate-Bewertung

| Kriterium | Schwellwert | Aktuell | Verdict |
|---|---|---|---|
| Gold Path Schritte | >= 7/8 (RC), 8/8 (RC_READY) | 8/8 | PASS |
| GP-06 (sicherheitskritisch) | PASS | PASS | PASS |
| Security Checks | 0 Blocker | 0 | PASS |
| Technische IDs in UI | 0 | 0 | PASS |
| Blocking 1.0 Schritte | Alle PASS | 8/8 | PASS |

**Gate-Entscheidung: RC_READY** (vorbehaltlich Product Maturity >= 85 und anderen RC-Kriterien)

Quelle: `reports/current/product_gold_path.json`
