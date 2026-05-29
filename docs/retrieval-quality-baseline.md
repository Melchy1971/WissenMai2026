# Retrieval Quality Baseline (M5)

Vor M5-Implementierung muss für alle Slices messbar sein, was "gute Suche" bedeutet. Die folgenden Metriken sind verbindlich und werden für jede Release- und Gate-Entscheidung automatisiert ausgewertet.

## 1. Precision
- **Definition:** Anteil der relevanten Treffer an allen gelieferten Treffern.
- **Messmethode:** TP / (TP + FP), gemessen auf Golden Queries.
- **Datenquelle:** Retrieval-API, Golden Dataset, Test-Queries.
- **Zielwert:** ≥ 0.90
- **Warnschwelle:** < 0.85
- **Gate-Schwelle:** < 0.80 → BLOCK

## 2. Recall
- **Definition:** Anteil der gefundenen relevanten Treffer an allen tatsächlich relevanten Treffern.
- **Messmethode:** TP / (TP + FN), gemessen auf Golden Queries.
- **Datenquelle:** Retrieval-API, Golden Dataset, Test-Queries.
- **Zielwert:** ≥ 0.90
- **Warnschwelle:** < 0.85
- **Gate-Schwelle:** < 0.80 → BLOCK

## 3. Citation Accuracy
- **Definition:** Anteil der korrekten Zitationen (richtige Quelle, richtige Stelle) an allen gelieferten Zitationen.
- **Messmethode:** Manuelle oder automatisierte Prüfung der Zitations-IDs und Offsets gegen Golden Dataset.
- **Datenquelle:** Retrieval-API, Golden Dataset, Citation-Log.
- **Zielwert:** ≥ 0.98
- **Warnschwelle:** < 0.95
- **Gate-Schwelle:** < 0.90 → BLOCK

## 4. Lifecycle Compliance
- **Definition:** Anteil der Treffer, deren Lifecycle-Status (z.B. published, archived) zum Query-Kontext passt.
- **Messmethode:** Abgleich Treffer-Status gegen Query-Kontext und Policy.
- **Datenquelle:** Retrieval-API, Dokument-Metadaten.
- **Zielwert:** 100%
- **Warnschwelle:** < 0.99
- **Gate-Schwelle:** < 0.98 → BLOCK

## 5. Source Status Accuracy
- **Definition:** Anteil der Treffer mit korrektem Source-Status (z.B. aktiv, archiviert, gelöscht).
- **Messmethode:** Abgleich Treffer-Source-Status gegen Golden Dataset.
- **Datenquelle:** Retrieval-API, Dokument-Metadaten, Golden Dataset.
- **Zielwert:** 100%
- **Warnschwelle:** < 0.99
- **Gate-Schwelle:** < 0.98 → BLOCK

## 6. Duplicate Retrieval Rate
- **Definition:** Anteil der Suchergebnisse, die Duplikate (gleicher Inhalt, gleiche Quelle) sind.
- **Messmethode:** Vergleich der Treffer-Hashes und Source-IDs pro Query.
- **Datenquelle:** Retrieval-API, Dokument-Metadaten.
- **Zielwert:** 0%
- **Warnschwelle:** > 0.1%
- **Gate-Schwelle:** > 0.5% → BLOCK

## 7. Hallucination Risk
- **Definition:** Anteil der Treffer, die nicht im Golden Dataset oder in der Datenbank existieren ("halluziniert").
- **Messmethode:** Abgleich aller Treffer gegen Golden Dataset und DB.
- **Datenquelle:** Retrieval-API, Golden Dataset, DB-Dump.
- **Zielwert:** 0%
- **Warnschwelle:** > 0.1%
- **Gate-Schwelle:** > 0.5% → BLOCK

---

**Hinweis:** Alle Metriken werden automatisiert berechnet und Gate-Entscheidungen dokumentiert. Schwellenwerte sind regelmäßig zu überprüfen und an die Datenbasis anzupassen.
