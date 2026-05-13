# Retrieval Regression Detection Report

Status: `pass`
Trigger: `reindex`
Dataset: `m5-retrieval-golden-v1`
Baseline vorhanden: `true`
Regression Delta: `0.05`

## Metriken

| Metrik | Wert | Schwelle |
|---|---:|---:|
| Precision@5 Search | 1.0 | 0.8 |
| Recall@5 Search | 1.0 | 0.85 |
| Precision@5 Chat | 1.0 | 0.75 |
| Recall@5 Chat | 1.0 | 0.8 |
| Citation Completeness | 1.0 | 0.9 |
| Missing Context Rate | 0.0 | <= 0.15 |
| Insufficient Context Accuracy | 1.0 | 0.95 |
| Lifecycle Violations | 0 | 0 |

## Regressionen

Keine Regression erkannt.

## Automatische Trigger

- Reindex
- Restore
- Cleanup
- Chunking-Aenderung
