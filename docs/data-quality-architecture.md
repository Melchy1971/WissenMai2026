# Data Quality Architektur (M5)

## 1. Duplicate Detection
- **Datenmodell:**
  - Dokumente, Chunks, Hashes, Source-IDs
- **Regeln:**
  - Kein Dokument/Chunk darf mehrfach mit identischem Hash und Source-ID existieren
- **Metriken:**
  - Anzahl Duplikate pro Dokumenttyp
  - Anteil Duplikate an Gesamtmenge
- **Reports:**
  - Duplikat-Report (JSON/Markdown)
- **Gates:**
  - Blockiert Import/Release, wenn Duplikat-Anteil > 0,5%

## 2. Missing Metadata Detection
- **Datenmodell:**
  - Dokumente, Chunks, Pflichtfelder (z.B. Titel, Datum, Autor, Source-ID)
- **Regeln:**
  - Alle Pflichtfelder müssen befüllt sein
- **Metriken:**
  - Anteil Dokumente/Chunks mit fehlenden Pflichtfeldern
- **Reports:**
  - Missing-Metadata-Report
- **Gates:**
  - Blockiert Import, wenn >1% der Einträge Metadaten fehlen

## 3. Empty Content Detection
- **Datenmodell:**
  - Chunks, Content-Feld
- **Regeln:**
  - Kein Chunk darf leeren Content haben
- **Metriken:**
  - Anteil leerer Chunks
- **Reports:**
  - Empty-Content-Report
- **Gates:**
  - Blockiert Import, wenn >0,1% Chunks leer sind

## 4. Chunk Quality Detection
- **Datenmodell:**
  - Chunks, Token-Anzahl, Satzstruktur, Zeichensatz
- **Regeln:**
  - Mindestlänge, keine reinen Sonderzeichen, keine reinen Stoppwörter
- **Metriken:**
  - Anteil Chunks unter Mindestlänge
  - Anteil Chunks mit Zeichenfehlern
- **Reports:**
  - Chunk-Quality-Report
- **Gates:**
  - Warn- und Blockschwellen werden im zugehoerigen Gate-Report dokumentiert.

## 5. Source Status Validation
- **Datenmodell:**
  - Dokumente, Source-Status (z.B. aktiv, archiviert, gelöscht)
- **Regeln:**
  - Nur aktive Quellen dürfen importiert werden
- **Metriken:**
  - Anteil Dokumente mit ungültigem Source-Status
- **Reports:**
  - Source-Status-Report
- **Gates:**
  - Blockiert Import, wenn ungültige Quellen >0,1%

## 6. Lifecycle Consistency
- **Datenmodell:**
  - Dokumente, Lifecycle-Status (z.B. imported, processed, published, archived)
- **Regeln:**
  - Statusübergänge müssen konsistent und erlaubt sein
- **Metriken:**
  - Anteil inkonsistenter Statusübergänge
- **Reports:**
  - Lifecycle-Consistency-Report
- **Gates:**
  - Blockiert Release, wenn inkonsistente Übergänge >0,1%

---

**Hinweis:** Alle Reports werden automatisiert erzeugt und Gate-Entscheidungen dokumentiert. Metriken und Schwellenwerte sind regelmäßig zu überprüfen und an die Datenbasis anzupassen.
