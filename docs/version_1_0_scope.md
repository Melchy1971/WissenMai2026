# Ruflo — Scope Version 1.0

**Stand:** 2026-06-15  
**Status:** DRAFT — PO-Freigabe ausstehend

---

## In Scope 1.0

### Dokumente
- Import (Datei-Upload, URL-Import)
- Dokumentliste mit Lifecycle-Status (pending / processing / chunked / error / archived)
- Dokumentdetail mit Textvorschau (Chunks)
- Archivieren, Wiederherstellen, Löschen (Soft-Delete)
- Tags zuweisen und anzeigen (nach P1-GAP-01/02 Implementierung)

### Import
- Einzelimport als Multipart-Upload oder URL
- Hintergrundverarbeitung via BackgroundJob
- Statuspolling bis Import-Abschluss
- Fehleranzeige bei status='error'

### Suche
- Volltextsuche über Dokument-Chunks (GET /search/chunks?q=)
- Ergebnisanzeige mit document_title und text_preview
- Workspace-isolierte Ergebnisse

### Themen (Topics)
- Themenliste (nach P1-GAP-01/02)
- Topic-Detail mit Quellen-Referenzen und Dokumentbezug
- Tags an Topics (nach P1-GAP-01/02)
- Topics werden aus Analyseergebnissen abgeleitet

### Datenanalyse
- Analyse-Job erstellen (Dokument(e) auswählen, Analyse-Typ wählen)
- Statusverfolgung (pending / running / completed / failed / cancelled)
- Ergebnis anzeigen (summary, suggested_topics, suggested_tags)
- Approval durch Workspace-Admin
- Job abbrechen (nach AGAP-02)

### Dashboard
- Übersicht: Dokument-Counts, Importe, Analysen, Themen, Datenqualität, Drift-Status
- Drift-Widget: Read-Only, zeigt Schweregrad-Zusammenfassung + Link zu /drift
- Alle Widgets: Empty State / Error State / Loading State

### Export
- Analyseergebnisse als JSON und Markdown
- Dokumente (Metadaten + Textinhalt) als JSON und Markdown
- Quellenangaben im Export erhalten
- Audit-Event bei jedem Export-Vorgang

### Benutzer
- Login und Logout
- Session-Revocation (Token wird bei Logout ungültig)
- Workspace-Rollentrennung: member / admin / owner
- Workspace-Isolation: Nutzer sieht nur Daten des eigenen Workspace

---

## Nicht Bestandteil von 1.0

### Cleanup
- Kein Cleanup-Button (PROHIBIT-06 — gilt permanent)
- Kein automatischer Daten-Bereinigungslauf
- M5c (Cleanup-Phase) ist NO_GO bis m5c_start_gate = PASS und PO-Sign-off vorliegt

### Repair / Governance Automation
- Kein Repair-Button (PROHIBIT-02 — gilt permanent)
- Kein automatisches Repair bei Drift-Befunden
- Drift Detection bleibt Read-Only
- Keine automatische M5c-Ausführung ohne PO-Approval je Proposal (PROHIBIT-08)

### Admin-Spezialwerkzeuge
- AdminDiagnosticsPage (/admin/diagnostics) ist nicht Teil des Endnutzer-Produkts
- RAG-Center (Debug-Ansicht mit In-Memory-Datenspeicher) nicht im Produktions-Scope
- Governance-Seite (/governance) nicht im Endnutzer-Scope
- Agents-Seite (/agents) nicht im Endnutzer-Scope
- Collaboration-Seite (/collaboration) nicht im Endnutzer-Scope

### Out-of-Scope-Features
- PDF-Export (P2 nach 1.0)
- Themen-Export (abhängig von Topics-Backend + Export-Center-Erweiterung)
- Semantische Suche / Vektorsuche (P3)
- Benutzerverwaltung per API (Einladen, Deaktivieren, Passwort-Reset) (P2)
- Profil-Bearbeitung / Passwort ändern (P2)
- Data Quality Trigger (POST /data-quality/runs) (P2, wird geplant nach 1.0)
- Multi-User Workspace Ausbau (P3)
- OCR für Bild-Dokumente (vorbereitet, kein Zeitplan)
- Bulk-Export (mehrere Quellen in einer Datei)
- Scheduled Data Quality Runs (automatisch)
- Chat mit LLM (UnconfiguredLlmProvider — nach LLM-Konfiguration, kein 1.0-Commitment)

---

## Vorbedingungen für 1.0-Release

Die folgenden Punkte müssen vor Release abgeschlossen sein:

1. **TEST_DATABASE_URL gesetzt** → Testpipeline ausführbar, Gates re-evaluierbar
2. **RCB-001 gelöst** → NAV_ITEMS mit Masterplan synchronisiert
3. **RCB-002 gelöst** → PO-Entscheidung zu Navigation-Optionen
4. **RCB-003 gelöst** → AdminRoute-Guard für /admin/diagnostics
5. **P1-GAP-01/02** → Topics ORM + API
6. **AGAP-02** → Cancel-Endpunkt für Analyse-Jobs
7. **AGAP-07** → AnalysisPage.jsx
8. **Export Center MVP** → JSON + Markdown für Dokumente + Analyseergebnisse
9. **LLM-Konfiguration** → PO stellt Provider + API-Key bereit
10. **Frontend Build** → release_manifest.frontend_build = PASS

---

## Scope-Entscheidungen (Begründung)

| Entscheidung | Begründung |
|---|---|
| Cleanup kein 1.0 | PROHIBIT-06 aktiv; M5c-Gate BLOCKED; Risiko zu hoch für ersten Release |
| Repair kein 1.0 | PROHIBIT-02 aktiv; Drift bleibt Read-Only per Designentscheidung |
| Chat mit LLM offen | LLM-Provider-Entscheidung PO-seitig offen; RuntimeError bei Start aktuell |
| PDF-Export P2 | Implementierungsaufwand zu hoch für MVP; JSON + Markdown decken Kernbedarf |
| Benutzerverwaltung P2 | Nutzeranlage direkt in DB akzeptabel für 1.0-Pilotbetrieb |
