# Ruflo Version 1.0 — Scope Freeze

**Stand:** 2026-06-15  
**Status:** FROZEN — keine Scope-Erweiterungen bis 1.0-Release  
**Gültig ab:** diesem Dokument

---

## In Scope — Version 1.0

Die folgenden Bereiche sind für Version 1.0 definiert und werden vollständig ausgeliefert:

### 1. Dashboard
- Widgets: Dokumente (W01), Importe (W02), Analysen (W03), Themen (W04), Datenqualität (W05), Drift (W06), Aktivitäten (W07)
- W06 Drift: Read-Only-Anzeige — kein Repair, kein Trigger, kein Cleanup
- Kein RepairButton, kein CleanupButton in keinem Dashboard-Widget

### 2. Dokumentenzentrum (Dokumente)
- Dokumentliste mit Sortierung und Statusfilter
- Dokumentdetail: Metadaten, Textvorschau (Chunks), Versionsverlauf
- Lifecycle: Archivieren, Wiederherstellen, Löschen (Soft-Delete)
- Tags: Anzeige (nach P1-GAP-01/02 Implementierung)
- Keine rohen technischen IDs (id, workspaceId, ownerUserId) im UI sichtbar

### 3. Import
- Datei-Upload (multipart) und URL-Import
- Unterstützte Formate: PDF, DOCX, TXT, Markdown
- BackgroundJob-Polling mit Statusanzeige
- Retry bei fehlgeschlagenem Import
- Duplicate-Erkennung

### 4. Suche
- Volltextsuche auf Chunk-Ebene (GET /api/v1/search/chunks)
- Relevanz-Anzeige (visuell, ohne technische Scores)
- Vorschau im Suchergebnis
- Keine technischen Chunk-IDs oder Vektor-Scores im UI

### 5. Themen (Topics)
- Themenliste mit Name, Zusammenfassung, Dokumentanzahl
- Themendetail: KI-Zusammenfassung, verknüpfte Dokumente, Quellen, Tags
- Lokale Namenssuche
- KI-Zusammenfassung: quellenbasiert, nachvollziehbar, manuell aktualisierbar
- Verknüpfte Themen anzeigen

### 6. Datenanalyse
- 7-Schritt-Workflow: Dokument wählen → Starten → Fortschritt → Ergebnis → Vorschläge → Freigabe → Übernahme
- Analyse-Job-Verlauf (Liste abgeschlossener und laufender Jobs)
- Freigabe (Approval) durch workspace_admin — manuell, niemals automatisch
- Cancel laufender Analysen
- Fehlerzustände mit Nutzerinformation

### 7. Export
- Formate: JSON, Markdown
- Exportquellen: Dokumente, Analyseergebnisse
- Pflichtfelder in jedem Export: Quellenangaben, Erstellungsdatum, Ersteller, Workspace-ID
- Workspace-Isolation: Export nur für eigene Workspace-Daten
- PDF-Export: OUT OF SCOPE für 1.0

### 8. Benutzerverwaltung
- Login / Logout
- Workspace-Mitgliedschaft (member / admin)
- Session-Revocation bei Logout
- Keine Self-Service-Registrierung (Admin erstellt Accounts)

---

## Nicht in Scope — Version 1.0

Die folgenden Bereiche sind explizit ausgeschlossen. Keine Implementierung, kein UI-Einstiegspunkt, keine versteckten Feature-Flags bis zum 1.0-Release.

### Cleanup
- Kein CleanupButton in irgendeiner Komponente (PROHIBIT-06)
- Keine automatische Bereinigung von Dokumenten, Chunks oder Analyse-Daten
- Kein Batch-Delete ohne explizite Nutzeraktion

### Repair
- Kein RepairButton in DriftDashboard oder anderen Komponenten (PROHIBIT-02)
- Keine automatische Reparatur von Drift-Zuständen
- Drift Detection ist Read-Only

### Governance Automation
- Keine automatische M5c-Ausführung (PROHIBIT-08)
- M5c Cleanup: NO-GO bis m5c_start_gate = PASS und PO-Sign-off vorliegt
- Keine automatischen Approval-Workflows — Freigabe ist immer eine explizite Nutzeraktion
- Kein automatisches Routing von Analyseergebnissen

### Spezial-Adminfunktionen
- Keine AdminDiagnosticsPage im produktiven UI sichtbar
- Kein direkter Datenbankzugriff über UI
- Keine Roh-Log-Anzeige im Frontend
- Keine Workspace-übergreifenden Admin-Operationen durch reguläre Nutzer
- Keine Token-Logging-Funktion
- Kein Credential-/Secret-Export

### Sonstige ausgeschlossene Features
- PDF-Export (technische Komplexität, in Version 1.1)
- Dokument-Inhalt bearbeiten (immutable — nur Metadaten editierbar, P2)
- Kategorien-Hierarchie (Kategorien als Konzept P3, Tags als flache Taxonomie für 1.0)
- Mobile-optimiertes UI (responsive Design P2)
- Mehrsprachigkeit / i18n (P3)
- SAML/SSO-Integration (P3)
- Bulk-Import (mehrere Dateien gleichzeitig — P2)

---

## Freeze-Bedingungen

1. Neuer Feature-Request nach diesem Dokument → automatisch in Backlog für 1.1
2. Bug-Fixes für In-Scope-Bereiche sind zulässig und erfordern keinen Scope-Change
3. Sicherheitskritische Fixes sind immer zulässig unabhängig vom Scope
4. Scope-Änderungen erfordern: schriftliche PO-Freigabe + Aktualisierung dieses Dokuments

---

## Referenzen

- `reports/current/product_release_gate.json` — Release-Entscheidung
- `reports/current/product_e2e_truth_suite.json` — E2E-Szenario-Bewertung
- `tasks/product_gap_tasks.md` — Sprint-Aufgaben zur Schließung der Lücken
- `docs/product_gap_sprint.md` — Sprint-Plan
