# GUI Product Gap Analysis

**Datum:** 2026-06-12
**Methode:** Abgleich aktuelle GUI (final_gui_scope.md + final_navigation.md) gegen fachlichen Nutzen aus Endanwendersicht
**Referenz:** docs/product_user_journey.md

---

## Bewertungsrahmen

Jede GUI-Funktion wird bewertet nach:
- **Nutzerwert**: Welchen fachlichen Nutzen hat der Anwender?
- **Sichtbarkeit**: Ist die Funktion auffindbar?
- **Vollständigkeit**: Kann der Anwender die Aufgabe abschließen?

---

## 1. Navigation — Ist vs. Soll

### Aktuelle Navigation (6 Punkte)

| Navigationspunkt | Route | Nutzerwert | Problem |
|-----------------|-------|-----------|---------|
| Dashboard | /dashboard | Mittel | Keine direkten Aktionen möglich |
| Suche | /chat | Hoch | Label "Suche" passt nicht — es ist ein Chat-Interface |
| Dokumente | /documents | Hoch | Gut, aber Import fehlt hier |
| Datenanalyse | /rag | Niedrig | Kombiniert Import + Analyse — beides getrennte Bedürfnisse |
| Data Quality | /data-quality | Niedrig für Endanwender | Technisch, keine Handlungsoptionen |
| Einstellungen | /settings | Niedrig (selten) | Korrekt platziert |

**Befund:** "Datenanalyse" ist falsch benannt für Import. Data Quality ist zu technisch für die Hauptnavigation. "Suche" führt zu einem Chat-Interface — Begriffsdiskrepanz.

---

## 2. Feature-Gap-Matrix

| Nutzerbedürfnis | Aktuell abgedeckt? | Lücke |
|-----------------|-------------------|-------|
| Dokument importieren | Teilweise — unter "Datenanalyse" versteckt | Falscher Navigationspunkt |
| Dokument suchen | Ja — /chat und /documents | Doppelter Einstieg verwirrt |
| Frage stellen (RAG) | Ja — /chat | Gut |
| Antwortquellen nachverfolgen | Ja — Citations in Chat | Gut, aber Link zum Dokument unklar |
| Themen / Kategorien durchstöbern | Nein | Nicht implementiert |
| Duplikate bereinigen | Nein | Absichtlich nicht freigegeben |
| OCR-Dokumente importieren | Nein | Kein OCR (KL-DEF-001) |
| Dokument bearbeiten | Nein | Read-only System — kein Schreibpfad |
| Mehrbenutzer / Rechte | Nein | Nicht implementiert |
| Export / Download | Nein | Nicht implementiert |

---

## 3. Kritische Lücken (Nutzersicht)

### Lücke 1: Import ist nicht auffindbar

Import ist der **Eintrittspunkt** der Anwendung. Ohne Import gibt es keine Dokumente, keine Suche, keine Antworten. Er liegt unter "Datenanalyse" — das ist der falsche Kontext. Ein Erstanwender findet Import nicht ohne Einweisung.

**Priorität:** Kritisch.

### Lücke 2: Fehlerpfad beim Import ohne Handlungsanweisung

Bei OCR_REQUIRED, PARSER_FAILED oder UNSUPPORTED_FILE_TYPE sieht der Anwender eine Fehlermeldung. Es gibt keinen Hinweis, was er tun soll (andere Datei, anderes Format, Konvertierung).

**Priorität:** Hoch.

### Lücke 3: Themen fehlen vollständig

Themen sind das fachliche Ordnungssystem einer Wissensbasis. Tags sind vorhanden (Datenmodell), aber keine UI dafür. Anwender können keine Wissensstruktur aufbauen.

**Priorität:** Hoch — aber Future Phase laut Masterplan.

### Lücke 4: Data Quality hat keine Nutzungskonsequenz

Data Quality zeigt Probleme, aber der Anwender kann nichts tun. Die Seite ist ein Reporting-Instrument für Admins, nicht für Endanwender. In der Hauptnavigation verursacht sie falsche Erwartungen.

**Priorität:** Mittel — aus Hauptnavigation herausnehmen oder in Dashboard-Widget integrieren.

### Lücke 5: Dashboard ist passiv

Das Dashboard zeigt Zahlen, hat aber keine durchklickbaren Aktionen. Ein Nutzer mit 3 fehlgeschlagenen Importen sieht die Zahl, aber kein "Jetzt prüfen"-Link.

**Priorität:** Mittel.

---

## 4. Redundanzen

| Redundanz | Bewertung |
|-----------|-----------|
| Suche in /chat UND Suche in /documents | Nicht zusammenführen — unterschiedliche Semantik (RAG vs. Volltextsuche). Aber klarer benennen: "Fragen" vs. "Suchen" |
| Importstatus im Dashboard UND in der Dokumentliste | Korrekt und sinnvoll — kein Handlungsbedarf |

---

## 5. Priorisierte Empfehlungen

| Prio | Maßnahme | Aufwand |
|------|----------|---------|
| 1 | Import als eigenen Navigationspunkt herauslösen | Niedrig — Routing-Änderung |
| 2 | "Suche" in "Suche / Fragen" umbenennen oder Doppeleinstieg klären | Niedrig |
| 3 | Data Quality aus Hauptnavigation → Dashboard-Widget oder Admin-Bereich | Niedrig |
| 4 | Dashboard-Widgets direktlinks zu Dokumenten und fehlgeschlagenen Importen | Mittel |
| 5 | Fehlerseiten mit konkreten Handlungsanweisungen anreichern | Mittel |
| 6 | Themen-UI implementieren | Hoch — Future Phase |
| 7 | Leere Dokumentliste mit Import-CTA | Niedrig |
