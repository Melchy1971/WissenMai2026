# MVP Scope Final

**Datum:** 2026-06-12
**Zweck:** Verbindliche Abgrenzung des MVP aus Produktsicht
**Nicht:** Technische Gate-Dokumentation — diese bleibt im Masterplan

---

## MVP-Definition

Der MVP liefert eine vollständige Wissensbasis für Teams: Dokumente importieren, durchsuchen, Fragen stellen, Wissen strukturieren. Alle technischen Hilfssysteme (Quality, Drift) laufen im Hintergrund und sind für den Endanwender nicht direkt sichtbar.

---

## Muss (MVP)

### Dokumentenverwaltung
- Dokumentliste mit Filter, Tags, Kategorien, Status
- Dokumentdetail (Metadaten, Zusammenfassung, Vorschau)
- Metadaten bearbeiten (Titel, Tags, Kategorie)
- Dokument archivieren
- Leere- und Fehlerzustände mit Handlungslinks

### Import
- Datei-Upload: TXT, MD, DOCX, DOC, PDF (mit extrahierbarem Text)
- Geführter Analyse-Workflow (7 Schritte)
- Importverlauf mit Status (läuft / erfolgreich / fehlgeschlagen)
- Verständliche Fehlermeldungen ohne technische Codes
- Duplikatschutz mit Nutzerhinweis

### Suche
- Volltextsuche über Dokumentenbestand
- Filter: Kategorie, Tags, Themen
- Trefferliste mit Quellenkontext, Relevanzklasse (hoch/mittel/niedrig)
- Keine technischen Scores oder IDs sichtbar

### Themen
- Themenübersicht
- Themendetail mit KI-Zusammenfassung
- Quellenanzeige und Dokumentbezug
- Frage zum Thema stellen (RAG mit Themenfilter)
- Export (PDF oder Markdown)
- Thema erstellen, bearbeiten, Dokument zuordnen

### Datenanalyse
- Geführter 7-Schritte-Analyse-Workflow
- Fragen stellen (RAG-Chat) mit Quellenangaben
- Analyseverlauf

### Einstellungen
- KI-Provider (nur Admin)
- Chunk-Einstellungen / Suchkonfiguration (nur Admin)
- Darstellung (alle)

### Rollenmodell
- Benutzer
- Administrator

---

## Optional (MVP-Plus, wenn Kapazität vorhanden)

### Data Quality (sichtbar)
- Dashboard-Widget "Qualitätshinweise" (verständliche Sprache)
- Detailansicht nur für Administratoren
- Kein direkter Report-Link für Endanwender

### Drift Detection (sichtbar)
- Abhängig von M5b Production Readiness PASS
- Wenn aktiv: Dashboard-Widget "Mögliche Änderungen im Wissensbestand"
- Kein technischer Drift-Report sichtbar

### Dokument löschen
- Nur für Administratoren
- Zwei-Schritt-Schutz (erst archivieren, dann löschen)

---

## Nicht MVP

| Feature | Begründung |
|---------|-----------|
| Cleanup-Operationen | Governance nicht freigegeben (PROHIBIT-02) |
| Repair-Aktionen | Governance nicht freigegeben (PROHIBIT-06, KL-GOV-001) |
| Governance-Admin-UI | Explizit aus Navigation entfernt |
| Gate-Management | Internes Steuerungsinstrument, kein Produktfeature |
| OCR-Verarbeitung | Nicht implementiert (KL-DEF-001) |
| Vektorsuche / Semantische Suche | Embeddings nicht implementiert (KL-DEF-002) |
| Streaming-Chat | Nicht Teil von M3c |
| Multi-Upload-Queue | Nicht Teil von M4b Scope |
| Backup/Restore-UI | Automatisierung fehlt |
| OAuth / SSO | Explizit nicht V1 |
| Benutzer-Verwaltung UI | Future Phase |
| Workspace-Verwaltung UI | Future Phase |
| Reviewer-Rolle | Future Phase |
| Auditor-Rolle | Future Phase |
| Export Dokumentinhalt | Datenschutz — kein Rohinhalt-Export |
| Admin-Diagnostics-Seite | Debug-Tool, kein Produktionsbestandteil |

---

## Grenzfälle

### Themen im MVP

Themen sind im Masterplan als "Future Phase" markiert und aktuell nicht implementiert. Aus Produktsicht sind sie für den MVP-Nutzwert zentral — sie verwandeln eine Dokumentensammlung in eine Wissensbasis.

**Entscheidung offen:** Themen-UI in MVP aufnehmen (erfordert Implementierung) oder als MVP-Plus einordnen.

### Data Quality Sichtbarkeit

Data Quality läuft bereits (M5a implementiert). Für Endanwender nur als übersetzte Qualitätshinweise sichtbar — kein technischer Report. Diese Entscheidung ist produktseitig getroffen und unabhängig vom technischen Gate-Status.

---

## Abgrenzung MVP vs. Masterplan

Der Masterplan steuert die technische Implementierungsreihenfolge und Gate-Freigaben. Dieser MVP-Scope ist die produktseitige Sicht: Was soll ein Endanwender im ersten Release nutzen können? Beide Sichten müssen übereinstimmen — wo sie abweichen, ist eine Entscheidung erforderlich.

Aktuelle Abweichungen:

| Bereich | Masterplan | MVP Scope |
|---------|-----------|-----------|
| Themen | Future Phase | Für MVP relevant — Implementierung erforderlich |
| Data Quality (UI) | M5a, BLOCKED | Nur als Qualitätshinweis sichtbar — umsetzbar ohne Gate-PASS |
| Suche-Label | "Chat" (/chat) | Getrennt in "Suche" + "Datenanalyse" |
