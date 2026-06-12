# Sucherfahrung

**Datum:** 2026-06-12
**Ziel:** Klare Trefferliste mit fachlichen Metadaten — keine technischen Interna sichtbar
**Route:** /search

---

## Konzept

Die Suche ist Volltextsuche über den Dokumentenbestand. Sie liefert Treffer auf Absatzebene (Chunk), zeigt Kontext, Quelle und Relevanz in verständlicher Sprache — keine Scores, keine IDs, keine technischen Feldnamen.

---

## Sucheinstieg

```
┌─────────────────────────────────────────────────────┐
│  Suche                                              │
│  ┌─────────────────────────────────┐ [Suchen]       │
│  │ Was suchen Sie?                 │                │
│  └─────────────────────────────────┘                │
│                                                     │
│  Filter: [Kategorie ▾] [Tags ▾] [Themen ▾]         │
└─────────────────────────────────────────────────────┘
```

---

## Trefferliste

### Je Treffer

```
┌─────────────────────────────────────────────────────┐
│  [Dokumenttitel]                    [Kategorie]      │
│  Thema: SAP-Prozesse  ·  Tags: #Q1 #SAP             │
│                                                     │
│  "…der Vorgang wird nach §3 Abs. 2 der internen     │
│   Richtlinie behandelt und erfordert eine           │
│   Genehmigung durch den Teamleiter…"                │
│                                                     │
│  Relevanz: ████░░  Hoch   ·  Importiert: 10.06.2026 │
│                                                     │
│  [Dokument öffnen]                                  │
└─────────────────────────────────────────────────────┘
```

### Felder je Treffer

| Feld | Inhalt | Anzeige |
|------|--------|---------|
| Titel | document.title | fett, klickbar |
| Kategorie | category.name | Chip oben rechts |
| Themen | Zugeordnete Themen | Zeilentext |
| Tags | Erste 5 Tags | Chips |
| Treffertext | text_preview des Chunks | kursiv in Anführungszeichen |
| Relevanz | Klasse (Sehr hoch / Hoch / Mittel) | Balken + Text |
| Importiert | created_at, formatiert | grau |
| Aktion | Link zu Dokumentdetail | Button |

### Nicht angezeigt

- ts_rank-Score (Zahl)
- chunk_id, document_id
- chunk_index, position
- source_anchor (technisch)
- Parser-Metadaten
- Gate-Status

---

## Relevanzkennzeichnung

Interne Scores werden in drei verständliche Klassen übersetzt:

| Score-Bereich | Anzeige | Farbe |
|--------------|---------|-------|
| Hoch (ts_rank ≥ 0.7) | "Sehr relevant" + voller Balken | grün |
| Mittel (0.3–0.7) | "Relevant" + halber Balken | gelb |
| Niedrig (< 0.3) | "Möglicherweise relevant" + kurzer Balken | grau |

Keine Dezimalzahlen, keine %-Angaben.

---

## Filter

### Kategoriefilter
- Dropdown mit allen Kategorien
- Mehrfachauswahl

### Tag-Filter
- Dropdown mit allen Tags
- Mehrfachauswahl
- Tags, die keine Treffer liefern würden, sind ausgegraut

### Themenfilter
- Dropdown mit allen Themen
- Beschränkt die Suche auf Dokumente dieses Themas

---

## Leer- und Fehlerzustände

| Zustand | Anzeige |
|---------|---------|
| Keine Eingabe | Suchfeld mit Platzhalter, leere Seite |
| Keine Treffer | "Keine Ergebnisse für '[Suchbegriff]'. Tipp: Allgemeineren Begriff versuchen." |
| Zu wenige Dokumente | "Nur [n] Dokumente durchsucht — importieren Sie mehr Wissen." |
| Suche nicht verfügbar | "Suche momentan nicht verfügbar. [Erneut versuchen]" |

---

## Abgrenzung zu "Fragen stellen" (RAG-Chat)

| | Suche (/search) | Datenanalyse / Chat (/rag) |
|--|----------------|---------------------------|
| Eingabe | Suchbegriff | Frage in Freitextform |
| Ausgabe | Trefferliste mit Dokumentausschnitten | Generierte Antwort mit Quellenangaben |
| Funktion | Dokumente finden | Fragen beantworten |
| Quellen | Immer sichtbar (alle Treffer) | Zitiert (aus Antwort abgeleitet) |
