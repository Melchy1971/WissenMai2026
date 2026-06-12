# Navigation Simplification

**Datum:** 2026-06-12
**Ziel:** Maximale Einfachheit, minimale Klicks, keine technische Navigation sichtbar
**Referenz:** docs/gui_product_gap_analysis.md, docs/final_navigation.md

---

## Designprinzipien

1. Jeder Navigationspunkt beschreibt eine Nutzerintention, kein technisches Konzept.
2. Technische Funktionen (Gates, Reports, Data Quality, Drift) sind für Endanwender nicht sichtbar.
3. Maximale Tiefe: 2 Ebenen (Hauptnavigation + kontextuelle Unternavigation im Screen).
4. Kein Menüpunkt, der eine leere oder gesperrte Seite zeigt.

---

## Neue Navigation (7 Punkte)

| # | Label | Route | Beschreibung | Aktuell |
|---|-------|-------|--------------|---------|
| 1 | Dashboard | /dashboard | Überblick — Dokumente, Importe, Aktivität | vorhanden |
| 2 | Dokumente | /documents | Alle Dokumente — Liste, Suche, Detail | vorhanden |
| 3 | Import | /import | Neue Dokumente importieren + Jobstatus | war: /rag |
| 4 | Suche | /search | Volltextsuche über Dokumentenbestand | war: /documents (Suchfeld) |
| 5 | Themen | /topics | Wissensbereiche, KI-Zusammenfassungen | nicht implementiert* |
| 6 | Datenanalyse | /rag | Analyse-Workflows, KI-Verarbeitung | war: /rag (Mischseite) |
| 7 | Einstellungen | /settings | KI-Provider, Darstellung, Workspace | vorhanden |

*Themen ist Future Phase. Bis zur Implementierung: Navigationspunkt zeigen, aber mit "Kommt bald"-Platzhalter — kein leerer 404.

---

## Abgelöste Navigationspunkte

| Alter Punkt | Neuer Ort |
|-------------|-----------|
| Suche (/chat) | Aufgeteilt: Freitext → Suche (/search), Chat/RAG → Datenanalyse (/rag) |
| Datenanalyse (/rag, Mischseite) | Import trennen (/import) + Analyse behalten (/rag) |
| Data Quality (/data-quality) | Dashboard-Widget (Qualitätshinweise) + Admin-Unterbereich |

---

## Unternavigation (kontextuell, nicht im Hauptmenü)

### Dokumente
- Dokumentliste (Standard)
- Dokumentdetail (bei Auswahl)
- Versionen (im Dokumentdetail, auf Anforderung)

### Import
- Neue Datei importieren
- Importverlauf (laufende + abgeschlossene Jobs)

### Datenanalyse
- Analyse starten
- Analyseverlauf
- Chat mit Wissensbasis (/chat bleibt intern, wird als "Fragen stellen" angeboten)

### Einstellungen
- KI-Provider
- Import & Suche (Chunk-Einstellungen)
- Darstellung (Dark Mode, Sprache)

---

## Admin-Unterbereich (nicht in Hauptnavigation)

Erreichbar nur für Administratoren über Einstellungen → Erweitert:

- Data Quality Details
- System-Diagnose
- Benutzer (Future Phase)
- Workspace-Verwaltung (Future Phase)

---

## Klickpfade — Vorher / Nachher

| Aufgabe | Vorher (Klicks) | Nachher (Klicks) |
|---------|----------------|-----------------|
| Frage stellen | Dashboard → Suche → Frage = 2 | Dashboard → Datenanalyse → Frage = 2 |
| Dokument importieren | Dashboard → Datenanalyse → Import-Tab = 3 | Dashboard → Import = 1 |
| Dokument finden | Dashboard → Dokumente → Suche = 3 | Dashboard → Suche = 1 |
| Importstatus prüfen | Dashboard → Datenanalyse → Status = 3 | Dashboard → Import → Verlauf = 2 |

---

## Hinweis: Chat vs. Suche

Der bisherige Navigationspunkt "Suche" (/chat) war ein RAG-Chat-Interface. Aus Nutzersicht sind das zwei verschiedene Bedürfnisse:

- **Suche**: "Welche Dokumente haben X?" → Volltextsuche, Liste von Treffern
- **Fragen stellen**: "Was sagt die Wissensbasis zu X?" → RAG, generierte Antwort mit Quellen

Beide Pfade bleiben erhalten — unter unterschiedlichen Labels im richtigen Kontext.
