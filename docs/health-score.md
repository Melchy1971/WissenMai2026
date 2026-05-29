# M5 Health Score

Stand: 2026-05-29

## Status

- Phase: Vorbereitung abgeschlossen
- Implementierung: nicht gestartet
- Freigabestatus: kein betrieblicher Score ohne reale Messgrundlage und PostgreSQL-Truth-Nachweis
- Die Existenz einer Formel ist kein Nachweis einer laufenden Berechnung

---

## Zweck

Definiert Formel, Gewichte, Statusklassen und Gate-Bezug des M5 Health Score.

---

## Komponenten und Gewichte

| Komponente | Gewicht | Quelle |
|---|---:|---|
| Data Quality | 25 % | `m5_data_quality_report.json` |
| Drift | 20 % | `m5_drift_report.json` |
| Queue Health | 15 % | Queue-Aging-Report, `m5_queue_backlog_age_seconds` |
| Search / Retrieval Health | 15 % | Retrieval-Benchmark-Report |
| Backup Freshness | 10 % | Backup-Manifest, `m5_backup_freshness_seconds` |
| Error Rate | 10 % | Strukturierte Logs, Error-Rate-Aggregation |
| Documentation Truth | 5 % | `documentation_truth_lint.json` |

Score-Formel: `sum(weight_i * component_score_i)`, alle Komponenten normalisiert auf [0.0, 1.0].

---

## Komponenten-Score-Berechnung

| Komponente | 1.0 (vollständig gesund) | 0.0 (komplett degradiert) |
|---|---|---|
| Data Quality | alle Fehlerregeln count = 0 | mindestens ein Fehler count > 0 |
| Drift | drift_score = 0 | drift_score ≥ 1.0 oder kritischer Drift |
| Queue Health | keine stale Jobs, queue_age_p95 < Warnschwelle | persistenter Backlog oder Dead-Letter-Wachstum |
| Search / Retrieval | alle Benchmark-Metriken ≥ Schwelle, keine Baseline-Regression | mindestens eine Metrik unter Schwelle |
| Backup Freshness | letztes Backup < 6 Tage alt | > 7 Tage oder Verify failed |
| Error Rate | error_rate ≤ 0.01 | error_rate ≥ 0.05 |
| Documentation Truth | lint errors = 0 | lint errors > 0 |

---

## Statusklassen

| Status | Score-Bereich | Bedeutung |
|---|---|---|
| `healthy` | ≥ 0.85 | Normalbetrieb |
| `degraded` | 0.60–0.84 | Mindestens eine Komponente unter Warnschwelle |
| `unhealthy` | < 0.60 | Maßnahme erforderlich |

`healthy` darf nicht berichtet werden, wenn eine hard-stop Regel verletzt ist (Lifecycle-Exclusion-Violations > 0, Backup-Freshness > 7 Tage, Restore-Verify failed).

---

## Berechnungsvoraussetzungen

Score darf erst als betrieblicher Zustand dokumentiert werden, wenn:
- alle Quell-Reports aktuell und maschinenlesbar unter `reports/current/` verfügbar sind
- PostgreSQL-Truth-Block `health_score` grün ist
- keine Quelle `unknown` zurückgibt

Fehlt eine Quelle: Komponente = `unknown`, Score = `unknown` statt `healthy`.

---

## Nicht-Scope

- Keine produktive Live-Berechnung behaupten
- Keine Gate-Freigabe allein aus Dokumentation ableiten
- Kein Behaupten eines gestarteten M5-Monitorings

---

## Implementierungsanker

- CLI: `python -m app.cli m5 health-score --workspace <id>`
- Report-Ziel: `reports/current/m5_health_score_report.json`
- Score-Definition: `backend/app/observability/m5_metrics.py`
- Truth-Test-Block: `health_score`
