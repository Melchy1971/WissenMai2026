# Dokumentzentrum

**Datum:** 2026-06-12
**Ziel:** Zentrale Ansicht für alle Dokumente — Endanwender ohne Systemwissen
**Keine technischen Gates, Reports oder Drift-Informationen**

---

## Konzept

Das Dokumentzentrum ist die primäre Verwaltungsansicht für den Wissensbestand. Es zeigt alle Dokumente in einem Workspace, ermöglicht Filtern, Suchen und schnelles Voranschauen — und bietet direkte Aktionen für häufige Aufgaben.

---

## Seitenaufbau

```
┌─────────────────────────────────────────────────────┐
│  Dokumente                    [+ Importieren]        │
├──────────────┬──────────────────────────────────────┤
│  FILTER      │  DOKUMENTLISTE                       │
│              │                                      │
│  Kategorie   │  ┌────────────────────────────────┐  │
│  [ ] Alle    │  │ Titel    │ Kategorie│ Status │…│  │
│  [ ] Recht   │  ├──────────┼──────────┼────────┼─┤  │
│  [ ] Technik │  │ Dok A    │ Recht    │ Aktiv  │…│  │
│  [ ] …       │  │ Dok B    │ Technik  │ Aktiv  │…│  │
│              │  │ Dok C    │ –        │ Fehler │…│  │
│  Status      │  └────────────────────────────────┘  │
│  [ ] Aktiv   │                                      │
│  [ ] Fehler  │  Treffer: 42     ◄ 1 2 3 … ►        │
│  [ ] Archiv  │                                      │
│              ├──────────────────────────────────────┤
│  Tags        │  SCHNELLVORSCHAU (rechts oder Modal) │
│  [ ] Q1      │                                      │
│  [ ] SAP     │  [Dokumenttitel]                     │
│  [ ] …       │  Kategorie · Tags · Status           │
│              │  Erstellt: 12.06.2026                │
│  [Filter     │                                      │
│   zurückset] │  Vorschautext (erste 300 Zeichen)    │
│              │  …                                   │
│              │  [Öffnen]  [Archivieren]  [Löschen]  │
└──────────────┴──────────────────────────────────────┘
```

---

## Dokumentliste

### Spalten

| Spalte | Inhalt | Sortierbar |
|--------|--------|-----------|
| Titel | document.title | ja |
| Kategorie | category.name | ja |
| Tags | Erste 3 Tags, dann "+n" | nein |
| Status | Aktiv / Archiviert / Fehler | ja |
| Importiert | created_at (formatiert) | ja |
| Aktionen | Schnellaktionen (Kebab-Menü) | nein |

### Status-Darstellung

| Wert | Label | Farbe |
|------|-------|-------|
| active | Aktiv | grün |
| archived | Archiviert | grau |
| deleted | Gelöscht | rot (nur kurz sichtbar) |
| pending | Import läuft | blau (animiert) |
| failed | Fehler | rot |
| ocr_required | PDF ohne Text | orange |

Technische Status-Werte (import_status, content_hash etc.) sind nicht sichtbar.

---

## Filter

### Kategoriefilter
- Mehrfachauswahl
- Zeigt nur Kategorien, die mindestens ein Dokument haben
- "Alle" deaktiviert alle einzelnen Filter

### Statusfilter
- Aktiv (Standard aktiv)
- Archiviert
- Fehler
- Import läuft

### Tag-Filter
- Mehrfachauswahl
- Nur Tags des aktuellen Workspace
- Suche innerhalb der Tag-Liste ab 10+ Tags

### Suchfeld (Volltext im Dokumenttitel und Tags)
- Suche läuft live beim Tippen (debounced 300ms)
- Sucht in title, tags, category
- Keine Chunk-Suche — dafür ist der Navigationspunkt "Suche" zuständig

---

## Schnellvorschau

Beim Klick auf eine Zeile öffnet sich rechts (Desktop) oder als Modal (Mobile) eine Vorschau:

- Titel, Kategorie, Tags, Status
- Erstellt am / Zuletzt aktualisiert
- Vorschautext: Erster Textabschnitt (max. 500 Zeichen)
- Aktionsbuttons (kontextabhängig, siehe unten)

---

## Aktionen

### Anzeigen
- Öffnet die Dokumentdetailansicht
- Zeigt vollständigen Inhalt, Versionen (auf Anforderung)
- Immer verfügbar

### Bearbeiten
- Öffnet Bearbeitungsformular für Metadaten: Titel, Kategorie, Tags
- Nicht verfügbar bei Status: failed, deleted
- Dokumentinhalt ist nicht bearbeitbar (System importiert, nicht bearbeitet)

### Archivieren
- Setzt Status auf "archived"
- Dokument bleibt in der Wissensbasis, wird aber aus der Suche ausgeschlossen
- Bestätigungsdialog: "Dieses Dokument wird nicht mehr in der Suche erscheinen."
- Umkehrbar: archivierte Dokumente können reaktiviert werden
- Nicht verfügbar bei Status: pending, deleted

### Löschen
- Soft Delete — Dokument wird auf "deleted" gesetzt
- Nur verfügbar wenn: status = archived (Zwei-Schritt-Schutz)
- Bestätigungsdialog mit Dokumentname
- Historische Citations bleiben erhalten (Quellenstabilität)
- Nicht umkehrbar über die UI

---

## Leer- und Fehlerzustände

| Zustand | Anzeige |
|---------|---------|
| Keine Dokumente im Workspace | "Noch keine Dokumente. [Jetzt importieren →]" |
| Filter ergibt keine Treffer | "Keine Dokumente gefunden. [Filter zurücksetzen]" |
| Ladefehler | "Dokumente konnten nicht geladen werden. [Erneut versuchen]" |
| Fehler-Dokument ausgewählt | Vorschau zeigt Fehlermeldung + Hinweis auf Import-Seite |

---

## Nicht enthalten

- Technische Gates oder Report-Status
- Drift-Informationen
- Chunk-Ansicht (nur im Dokumentdetail auf Anforderung)
- Versionsverlauf (nur im Dokumentdetail auf Anforderung)
- Admin-Aktionen (Reindex, Repair, Cleanup)
