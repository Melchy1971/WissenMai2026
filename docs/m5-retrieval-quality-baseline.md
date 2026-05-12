# M5 Retrieval Quality Baseline

Status: implementiert als wiederholbarer Benchmark-Runner.

## Zweck

M5 bewertet Search und Chat Retrieval nicht nur qualitativ, sondern gegen ein festes Golden Dataset mit quantitativen Schwellen.

## Runner

```powershell
Set-Location backend
python -m app.cli m5 retrieval-benchmark
```

Reports:

- `reports/m5_retrieval/YYYYMMDD_HHMMSS.json`
- `reports/m5_retrieval/latest.json`
- `reports/m5_retrieval_summary.md`

## Golden Dataset

Dataset-Version: `m5-retrieval-golden-v1`

Der Benchmark enthaelt Golden Queries fuer:

- Upload-Job-Status
- Duplicate Handling
- Queue Recovery
- Dead-Letter Replay
- Lifecycle Search
- historische Citations
- Search Index Drift
- Backup/Restore
- Workspace-Grenzen fuer Jobs
- No-Answer Query fuer `insufficient_context`

## Metriken

| Metrik | Schwelle |
|---|---:|
| Search Precision@5 | >= 0.80 |
| Search Recall@5 | >= 0.85 |
| Search MRR | >= 0.85 |
| Chat Precision@5 | >= 0.75 |
| Chat Recall@5 | >= 0.80 |
| Chat MRR | >= 0.80 |
| Citation Completeness | >= 0.90 |
| Insufficient Context Accuracy | >= 0.95 |
| Lifecycle Exclusion Violations | 0 |

## Stop-Regel

Der Benchmark ist `failed`, wenn eine Metrik die Schwelle unterschreitet oder wenn archivierte/geloeschte Chunks in Search oder neuem Chat Retrieval erscheinen.
