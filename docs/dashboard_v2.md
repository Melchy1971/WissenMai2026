# Dashboard v2

**Datum:** 2026-06-12
**Ziel:** Endanwender-Dashboard — aktionsorientiert, kein technischer Status sichtbar
**Keine Gates, Reports oder technische Systeminfos**

---

## Designprinzip

Jedes Widget beantwortet eine Frage, die ein Anwender stellt, wenn er die Anwendung öffnet. Jedes Widget, das ein Problem zeigt, bietet einen direkten Handlungslink.

---

## Widget-Übersicht (6 Widgets)

```
┌─────────────────────────────────────────────────────┐
│  Guten Morgen, Markus.                              │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  DOKUMENTE   │  │NEUE IMPORTE  │  │ OFFENE    │  │
│  │              │  │              │  │ ANALYSEN  │  │
│  │  247         │  │  3 heute     │  │  2 warten │  │
│  │  Dokumente   │  │  1 fehlgesch.│  │ auf Prüfg.│  │
│  │              │  │              │  │           │  │
│  │ [Alle ansehen│  │[Import prüfen│  │[Jetzt prüf│  │
│  │  →]          │  │ →]           │  │ en →]     │  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  THEMEN      │  │SUCHAKTIVITÄT │  │QUALITÄTS- │  │
│  │              │  │              │  │HINWEISE   │  │
│  │  8 Themen    │  │ 42 Suchen    │  │           │  │
│  │  2 neue Dok. │  │ diese Woche  │  │ 2 Hinweise│  │
│  │              │  │              │  │ (Mittel)  │  │
│  │ [Themen →]   │  │[Suche →]     │  │[Ansehen →]│  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Widget 1: Dokumente

**Frage des Anwenders:** "Wie viele Dokumente habe ich?"

| Element | Inhalt |
|---------|--------|
| Zahl | Anzahl aktiver Dokumente |
| Subtext | "Davon [n] neu diese Woche" (wenn > 0) |
| Link | → Dokumentzentrum (/documents) |

**Nicht anzeigen:** Archivierte Dokumente, gelöschte Dokumente, technische IDs.

---

## Widget 2: Neue Importe

**Frage des Anwenders:** "Was ist seit gestern passiert?"

| Element | Inhalt |
|---------|--------|
| Zahl | Anzahl Imports letzte 24h |
| Subtext grün | "[n] erfolgreich" |
| Subtext rot | "[n] fehlgeschlagen" — nur wenn > 0 |
| Link | → Import-Verlauf (/import) |

Wenn kein Fehler: kein roter Subtext. Wenn alles leer: "Keine neuen Importe."

**Nicht anzeigen:** Job-IDs, technische Fehlercodes (intern), Parsernamen.

---

## Widget 3: Offene Analysen

**Frage des Anwenders:** "Gibt es etwas, das auf mich wartet?"

| Element | Inhalt |
|---------|--------|
| Zahl | Anzahl Dokumente in Schritt 5–6 des Analyse-Workflows (warten auf Freigabe) |
| Subtext | "Warten auf Ihre Freigabe" |
| Link | → Datenanalyse (/rag), Warteschleife |

Wenn nichts offen: "Keine offenen Analysen." (kein Handlungsdruck)

---

## Widget 4: Themen

**Frage des Anwenders:** "Welche Wissensbereiche habe ich?"

| Element | Inhalt |
|---------|--------|
| Zahl | Anzahl Themen |
| Subtext | "[n] Themen mit neuen Dokumenten" |
| Link | → Themenzentrum (/topics) |

Wenn Themen nicht implementiert: Widget ausblenden (Future Phase).

---

## Widget 5: Suchaktivität

**Frage des Anwenders:** "Wird die Wissensbasis genutzt?"

| Element | Inhalt |
|---------|--------|
| Zahl | Anzahl Suchanfragen letzte 7 Tage |
| Subtext | "Häufigste Suche: [Top-Begriff]" |
| Link | → Suche (/search) |

**Nicht anzeigen:** Nutzernamen, Sessions, interne Suchpfade.

---

## Widget 6: Qualitätshinweise

**Frage des Anwenders:** "Gibt es Probleme, die ich kennen sollte?"

| Element | Inhalt |
|---------|--------|
| Zahl | Anzahl offener Hinweise |
| Stufe | Niedrig / Mittel / Hoch (kein technischer Score) |
| Beispiele | "3 Dokumente könnten veraltet sein" / "2 mögliche Duplikate gefunden" |
| Link | → Detailansicht der Hinweise (kein Data-Quality-Report) |

Hinweise werden in verständliche Sprache übersetzt:

| Technischer Befund | Anwendertext |
|--------------------|--------------|
| duplicate_candidate | "Mögliches Duplikat gefunden" |
| missing_metadata | "Dokument ohne Kategorie oder Tags" |
| stale_content | "Dokument wurde lange nicht aktualisiert" |
| ocr_required | "PDF enthält keinen lesbaren Text" |

**Nicht anzeigen:** DQ Score (Zahl), Gate-Status, Report-Links, Drift-Details.

---

## Zeitlicher Kontext

- Widgets zeigen standardmäßig die letzten 24h für Importe, 7 Tage für Suchaktivität
- Kein Datum-Picker auf dem Dashboard — zu komplex
- "Aktualisiert vor [n] Minuten" unter dem Dashboard (einmalig, nicht je Widget)

---

## Nicht enthalten

- Systemstatus (API OK / DB erreichbar) — gehört in Admin-Bereich
- Gate-Widgets (M5a, M5b, M5c)
- Report-Status oder Report-Links
- Technische Kennzahlen (Chunk-Count, Parser-Version, Search-Vector-Status)
- Debug-Informationen
