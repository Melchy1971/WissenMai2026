# Themenzentrum

**Datum:** 2026-06-12
**Ziel:** Themen als primäres Wissenszentrum — strukturierter Zugang zum Dokumentenbestand
**Status:** Konzept (Implementierung: Future Phase)

---

## Konzept

Themen (Topics) sind das fachliche Ordnungssystem der Wissensbasis. Während Dokumente die Roheinheit sind, sind Themen die Bedeutungseinheit. Ein Thema fasst mehrere Dokumente zusammen, zeigt eine KI-generierte Zusammenfassung und ermöglicht den gezielten Einstieg in einen Wissensbereich.

**Unterschied zu Tags:** Tags sind Schlagworte, die ein Dokument beschreiben. Themen sind übergeordnete Wissenscluster, die Dokumente und Tags verbinden.

---

## Themenübersicht (Startseite /topics)

```
┌─────────────────────────────────────────────────────┐
│  Themen                         [Suche in Themen]   │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │
│  │ SAP-Prozesse │ │ Datenschutz  │ │ Onboarding  │  │
│  │ 12 Dokumente │ │ 7 Dokumente  │ │ 4 Dokumente │  │
│  │ Zuletzt: Mo  │ │ Zuletzt: Fr  │ │ Zuletzt: Mi │  │
│  │ [Öffnen]     │ │ [Öffnen]     │ │ [Öffnen]    │  │
│  └──────────────┘ └──────────────┘ └─────────────┘  │
│                                                     │
│  ┌──────────────┐ ┌──────────────┐                  │
│  │ IT-Security  │ │ HR-Richtlinien│                 │
│  │ 9 Dokumente  │ │ 6 Dokumente  │                  │
│  │ [Öffnen]     │ │ [Öffnen]     │                  │
│  └──────────────┘ └──────────────┘                  │
└─────────────────────────────────────────────────────┘
```

---

## Themendetail (/topics/:id)

### KI-Zusammenfassung

- Automatisch generierte Zusammenfassung der zugeordneten Dokumente
- Wird bei neuen Importen aktualisiert
- Zeigt Kerninhalte, nicht einzelne Dokumente
- Format: 3–5 Sätze oder Aufzählung der wichtigsten Punkte

### Quellenanzeige

- Liste aller Dokumente, die zu diesem Thema gehören
- Anzeige: Titel, Status (aktiv/archiviert), Importdatum
- Klick öffnet Dokumentdetail

### Dokumentbezug

- Jedes Dokument kann einem oder mehreren Themen zugeordnet sein
- Zuordnung: manuell durch Anwender oder KI-Vorschlag
- KI-Vorschläge sind als solche markiert ("Vorgeschlagen")

### Tag-Bezug

- Themen zeigen alle Tags, die in zugeordneten Dokumenten vorkommen
- Klick auf Tag filtert Dokumentliste auf dieses Tag

---

## Aktionen

| Aktion | Verfügbar für |
|--------|--------------|
| Thema ansehen | alle Anwender |
| Frage zum Thema stellen | alle Anwender — öffnet Chat mit Themenkontext |
| Thema erstellen | alle Anwender |
| Dokument zu Thema hinzufügen | alle Anwender |
| Thema exportieren | alle Anwender |
| Thema umbenennen | Ersteller oder Admin |
| Thema löschen | Admin |

---

## Export

- Format: PDF oder Markdown
- Inhalt: KI-Zusammenfassung + Quellenverzeichnis (Dokumenttitel, Datum)
- Kein Export von Rohinhalten (Datenschutz)

---

## Frage zum Thema stellen

- Öffnet das Chat-Interface mit vorgesetztem Themenfilter
- RAG-Kontext ist auf die Dokumente des Themas beschränkt
- Antwort zeigt, aus welchen Dokumenten innerhalb des Themas sie stammt

---

## Nicht enthalten

- Technische IDs oder Chunk-Referenzen
- Gate- oder Report-Status
- Drift Detection
- Embedding-Details
