# M5 Longrun Simulation

Status: implementiert als beschleunigte Betriebs-Simulation.

## Zweck

M5 prueft Stabilitaet ueber Zeit: wiederholte Uploads, Queue-Recovery, Lifecycle-Wechsel, Reindex, Drift Detection, Cleanup Dry-Run, Restore-Zyklen sowie paralleles Search/Chat-Verhalten.

## Runner

```powershell
Set-Location backend
python -m app.cli m5 longrun-simulation --cycles 28 --restore-every 7
```

Reports:

- `historische M5-Longrun-Archivkopie`
- `reports/current/masterplan_status.json`
- `reports/current/masterplan_status.json`

## Simulationsmodell

- 1 Zyklus entspricht einem simulierten Betriebstag.
- Restore wird standardmaessig alle 7 Zyklen simuliert.
- Reindex laeuft nach jedem Lifecycle-/Upload-Block und muss stale Index Entries wieder auf 0 bringen.
- Cleanup bleibt Dry-Run und darf keine geschuetzten Daten als loeschbar behandeln.

## Metriken

| Metrik | Stop-Kriterium |
|---|---:|
| stale_index_growth | > 0 |
| queue_backlog | > 25 |
| orphan_growth | > 0 |
| retrieval_precision_at_5 | < 0.80 |
| retrieval_recall_at_5 | < 0.85 |
| error_rate | > 0.05 |

## Statusklassen

- `pass`: keine Stop-Kriterien und keine Warnungen.
- `degraded`: keine Stop-Kriterien, aber Warnungen.
- `failed`: mindestens ein Stop-Kriterium verletzt.

