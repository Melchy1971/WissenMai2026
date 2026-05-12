# M5 Retrieval Quality Baseline

Dataset: `m5-retrieval-golden-v1`
Status: `pass`

| Metrik | Wert | Schwelle |
|---|---:|---:|
| search_precision_at_5 | 1.0 | 0.8 |
| search_recall_at_5 | 1.0 | 0.85 |
| search_mrr | 1.0 | 0.85 |
| chat_precision_at_5 | 1.0 | 0.75 |
| chat_recall_at_5 | 1.0 | 0.8 |
| chat_mrr | 1.0 | 0.8 |
| citation_completeness | 1.0 | 0.9 |
| insufficient_context_accuracy | 1.0 | 0.95 |
| lifecycle_exclusion_violations | 0 | 0 |

## Golden Queries

- `GQ-001` Wie funktioniert der Upload-Job-Status?
- `GQ-002` Wann wird ein Import als Duplicate erkannt?
- `GQ-003` Wie wird ein stale running Job recovered?
- `GQ-004` Was passiert beim Dead-Letter Replay?
- `GQ-005` Welche Dokumente erscheinen nach Archivierung in der Suche?
- `GQ-006` Wie werden historische Citations bei geloeschten Dokumenten angezeigt?
- `GQ-007` Wie wird Search Index Drift erkannt?
- `GQ-008` Welche Schritte gehoeren zum Restore?
- `GQ-009` Welche Workspace-Grenzen gelten fuer Jobs?
- `GQ-010` Wie starte ich eine Cloud-Replikation?
