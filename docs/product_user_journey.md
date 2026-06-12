# Product User Journey

**Datum:** 2026-06-12
**Perspektive:** Endanwender — kein Systemwissen vorausgesetzt
**Referenz:** masterplan.md, docs/final_gui_scope.md, docs/final_navigation.md

---

## Fachlicher Nutzen der Anwendung

Die Anwendung ist ein lokales Wissenssystem. Anwender importieren Dokumente, stellen Fragen und erhalten Antworten mit direktem Quellenverweis. Der Unterschied zu einer einfachen Suche: Die Antwort wird aus dem Dokumentinhalt generiert — nicht aus dem Internet.

**Kernversprechen:** "Frag deine eigenen Dokumente."

---

## 1. User Journey — Hauptpfad

### Journey: "Ich will eine Frage aus meinem Dokumentenbestand beantworten"

```
Login
  │
  ▼
Dashboard
  │  Überblick: Wieviele Dokumente? Gibt es neue Importe?
  │
  ▼
Suche (Chat)
  │  Frage eingeben
  │  Antwort mit Quellenverweis lesen
  │  Bei Bedarf: Quelle aufrufen → Dokument
  │
  ▼
Dokument-Detailansicht
     Volltext lesen, Version prüfen
```

**Klicks bis zur Antwort:** Login → Chat → Frage stellen = 3 Schritte (Ziel: 2 nach Verbesserung)

---

### Journey: "Ich will ein neues Dokument verfügbar machen"

```
Login
  │
  ▼
Import (aktuell: Datenanalyse / RAG Center)
  │  Datei hochladen
  │  Importstatus abwarten
  │
  ▼
Dokumente
  │  Dokument in der Liste prüfen
  │  Status: active / failed / pending
  │
  ▼
Suche
     Prüfen, ob das Dokument gefunden wird
```

**Klicks:** 4 Navigationsschritte, weil Import und Dokumentliste getrennte Bereiche sind.

---

### Journey: "Ich will den Zustand meines Wissensbestands prüfen"

```
Login
  │
  ▼
Dashboard
  │  Kennzahlen lesen: Dokumentanzahl, Importstatus, DQ Score
  │
  ▼
Data Quality
     Probleme lesen (read-only)
     → Sackgasse: keine Reparaturmöglichkeit für den Anwender
```

---

## 2. Hauptanwendungsfälle

| # | Anwendungsfall | Einstiegspunkt | Ergebnis |
|---|----------------|----------------|----------|
| H1 | Frage stellen | Suche (Chat) | Antwort mit Quellenverweis |
| H2 | Dokument importieren | Datenanalyse | Dokument in der Wissensbasis |
| H3 | Dokumentbestand durchsuchen | Dokumente | Gefundenes Dokument |
| H4 | Importstatus prüfen | Dokumente / Dashboard | Status active / failed |

---

## 3. Nebenanwendungsfälle

| # | Anwendungsfall | Einstiegspunkt | Ergebnis |
|---|----------------|----------------|----------|
| N1 | Dokumentdetail ansehen | Dokumente → Detail | Stammdaten, Versionen, Chunks |
| N2 | Versionsverlauf prüfen | Dokumentdetail | Read-only Liste der Versionen |
| N3 | Datenqualität prüfen | Data Quality | Score, Findings (read-only) |
| N4 | KI-Provider konfigurieren | Einstellungen → Provider | Modell, URL, Timeout |
| N5 | Chat-Session fortsetzen | Suche → Session-Detail | Verlauf lesen, Frage ergänzen |

---

## 4. Sackgassen

Sackgassen sind Stellen, an denen der Anwender ein Problem sieht, aber keine Handlungsmöglichkeit hat.

| Sackgasse | Wo | Problem | Ursache |
|-----------|-----|---------|---------|
| S1 | Data Quality | Findet Dubletten, fehlende Metadaten — aber keine Reparaturaktion | Repair ist im Masterplan nicht freigegeben (KL-GOV-001) |
| S2 | Dokumentdetail | Chunks sichtbar, aber nicht bearbeitbar | M3a ist read-only |
| S3 | Import schlägt fehl (Parser-Fehler) | Fehlermeldung sichtbar, kein Retry, kein Korrekturhinweis | Kein Retry-Flow in der GUI |
| S4 | Import schlägt fehl (OCR_REQUIRED) | PDF wird erkannt, aber nicht verarbeitet | OCR nicht implementiert (KL-DEF-001) |
| S5 | Dokumentliste leer | Leerer Workspace — kein direkter Link zum Import | Fehlender Durchlinkung |
| S6 | Themen (Topics) | Im Navigationskonzept vorgesehen, nicht implementiert | Future Phase |

---

## 5. Überflüssige Schritte

| # | Schritt | Warum überflüssig | Empfehlung |
|---|---------|-------------------|------------|
| Ü1 | Import unter "Datenanalyse" suchen | Import ist Kernfunktion, nicht Analyse | Eigener Navigationspunkt "Import" |
| Ü2 | Dashboard → Dokumente → Detail (3 Klicks zum Dokument) | Dashboard zeigt keine direkt anklickbaren Dokumente | Dashboard-Widgets sollen direkt verlinken |
| Ü3 | Data Quality als separater Navigationspunkt | Qualitätsinfos gehören zur Dokumentansicht | In Dokumentdetail oder Dashboard-Widget integrieren |
| Ü4 | Chunk-Ansicht im Dokumentdetail | Für Endanwender ohne Relevanz — technisches Konzept | Ausblenden oder in "Technische Details" falten |
| Ü5 | Versionen-Ansicht als eigenständiger Screen | Für 99 % der Nutzer irrelevant | Nur auf Anforderung zeigen |

---

## 6. Doppelte Funktionen

| Funktion | Vorkommen 1 | Vorkommen 2 | Bewertung |
|----------|------------|------------|-----------|
| Volltextsuche | Suche (Chat-Interface, /chat) | Dokumentliste (/documents, Suchfeld) | Zwei getrennte Sucheinstiege mit unterschiedlicher Semantik — zu erklären oder zu vereinen |
| Importstatus | Dashboard-Widget | Dokumentliste (Statusspalte) | Redundant, aber sinnvoll — Dashboard gibt Überblick, Liste gibt Detail |
| Dokumentanzahl | Dashboard-Widget | Dokumentliste (Paginierung) | Unkritisch |
| Fehlerdarstellung | Dokumentliste | Dokumentdetail | Korrekt — konsistente Fehlerdarstellung ist kein Problem |
