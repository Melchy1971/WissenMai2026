# M5 Retrieval Quality Baseline

Status: implementiert als wiederholbarer Benchmark-Runner.

## Zweck

M5 bewertet Search und Chat Retrieval nicht nur qualitativ, sondern gegen ein festes Golden Dataset mit quantitativen Schwellen.

## Runner

```powershell
Set-Location backend
python -m app.cli m5 retrieval-benchmark
```

Trigger-spezifische Regression Detection:

```powershell
python -m app.cli m5 retrieval-benchmark --trigger reindex
python -m app.cli m5 retrieval-benchmark --trigger restore
python -m app.cli m5 retrieval-benchmark --trigger cleanup
python -m app.cli m5 retrieval-benchmark --trigger chunking
```

Baseline bewusst aktualisieren:

```powershell
python -m app.cli m5 retrieval-benchmark --set-baseline
```

Reports:

- `historische M5-Retrieval-Archivkopie`
- `reports/current/masterplan_status.json`
- `reports/current/masterplan_status.json`
- `historische M5-Retrieval-Regression-Archivkopie`
- `reports/current/masterplan_status.json`
- `reports/current/masterplan_status.json`
- `reports/current/masterplan_status.json`

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
| Missing Context Rate | <= 0.15 |
| Lifecycle Exclusion Violations | 0 |

## Regression Detection

Regression Detection vergleicht jeden aktuellen Lauf gegen:

1. absolute Schwellenwerte
2. die gespeicherte Baseline in `reports/current/masterplan_status.json`

Regression Threshold:

- maximal erlaubter Rueckgang gegen Baseline: `0.05`
- gilt fuer Search Precision@5, Search Recall@5, Chat Precision@5, Chat Recall@5 und Citation Completeness
- maximal erlaubter Anstieg fuer Missing Context Rate gegen Baseline: `0.05`

Automatische Pflichtausloeser:

| Trigger | CLI-Wert | Pflicht |
|---|---|---|
| Reindex | `--trigger reindex` | nach jedem Reindex |
| Restore | `--trigger restore` | nach Restore und Reindex-after-Restore |
| Cleanup | `--trigger cleanup` | nach Cleanup Dry-Run und vor jedem mutierenden Cleanup |
| Chunking-Aenderung | `--trigger chunking` | nach Aenderungen an Chunking, Parser-Normalisierung oder Context Builder |

Report-Status:

- `pass`: keine Schwellenverletzung und keine Baseline-Regression
- `failed`: mindestens eine absolute Schwelle verletzt oder Baseline-Delta ueberschritten

Die Baseline darf nur mit `--set-baseline` aktualisiert werden. Eine Baseline-Aktualisierung braucht eine dokumentierte Begruendung im Change-/Retrieval-Stability-Assessment.

## Stop-Regel

Der Benchmark ist `failed`, wenn eine Metrik die Schwelle unterschreitet, Missing Context Rate die Obergrenze ueberschreitet, die Baseline-Regression groesser als `0.05` ist oder wenn archivierte/geloeschte Chunks in Search oder neuem Chat Retrieval erscheinen.

