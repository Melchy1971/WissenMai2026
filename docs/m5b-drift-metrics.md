# M5b Drift Detection — Metrics

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `drift_metrics.schema.json`.
Severity-Referenz: `drift_severity_matrix.json`.

---

## Überblick

8 Kennzahlen decken den vollständigen Drift-Erkennungsbereich ab. Alle Kennzahlen sind workspace-scoped; kein Cross-Workspace-Aggregat.

| Kennzahl | Typ | Zielwert | Warnschwelle |
|----------|-----|----------|--------------|
| `total_checks` | count | — | — |
| `total_drifts` | count | 0 | > 0 |
| `critical_drifts` | count | 0 | ≥ 1 → Gate NO_GO + Freeze |
| `warning_drifts` | count | 0 | > konfiguriert → Watch-Flag |
| `drift_rate` | ratio | 0.0 | > 0.01 |
| `retrieval_drift_rate` | ratio | 0.0 | > 0.05 |
| `lifecycle_drift_rate` | ratio | 0.0 | > 0.0 (jedes lifecycle_drift ist error) |
| `source_status_drift_rate` | ratio | 0.0 | > 0.0 (pro Workspace) |

---

## Kennzahl: total_checks

**Definition:** Anzahl aller durchgeführten Einzelprüfungen in einem DriftRun für einen Workspace.

**Formel:**
```
total_checks = COUNT(validation_steps_executed) per workspace per run
```

**Datenquelle:** DriftRun-Metadaten (Protokoll der ausgeführten Validierungsschritte)

**Zielwert:** Deterministisch; entspricht der Anzahl der konfigurierten Prüfungen. Abweichungen zwischen Runs bei gleicher Datenmenge deuten auf fehlgeschlagene Checks hin.

**Warnschwelle:** `total_checks < expected_checks` → Warn-Flag im Report (unvollständiger Scan)

---

## Kennzahl: total_drifts

**Definition:** Anzahl aller erzeugten Drift-Findings in einem DriftRun, unabhängig von Severity und Typ.

**Formel:**
```
total_drifts = COUNT(findings) per workspace per run
```

**Datenquelle:** `drift_report.json` → `findings` Array

**Zielwert:** 0

**Warnschwelle:** > 0 → Watch-Flag; Typ und Severity entscheiden über Gate-Effekt

---

## Kennzahl: critical_drifts

**Definition:** Anzahl der Findings mit `severity=critical` in einem DriftRun.

**Formel:**
```
critical_drifts = COUNT(findings WHERE severity = 'critical') per workspace per run
```

**Datenquelle:** `drift_report.json` → `findings` gefiltert auf severity=critical

**Zielwert:** 0

**Warnschwelle:** ≥ 1 → Gate NO_GO + Workspace-Freeze (sofortige Eskalation, keine weitere Aggregation nötig)

---

## Kennzahl: warning_drifts

**Definition:** Anzahl der Findings mit `severity=warning` in einem DriftRun.

**Formel:**
```
warning_drifts = COUNT(findings WHERE severity = 'warning') per workspace per run
```

**Datenquelle:** `drift_report.json` → `findings` gefiltert auf severity=warning

**Zielwert:** 0

**Warnschwelle:** > konfigurierter Schwelle (Standard: 5 je Run) → erhöhter Watch-Flag im Report

**Constraint:** `warning_drifts` darf unter keinen Umständen allein eine Gate-Blockade auslösen.

---

## Kennzahl: drift_rate

**Definition:** Anteil der Entitäten mit mindestens einem Drift-Finding an der Gesamtzahl geprüfter Entitäten in einem Workspace.

**Formel:**
```
drift_rate = COUNT(distinct entity_id WITH findings) / total_checks
```

**Datenquelle:** `drift_report.json` (findings.entity_id) + DriftRun.total_checks

**Zielwert:** 0.0

**Warnschwelle:** > 0.01 (1 %) → erhöhter Watch-Flag; Gate-Entscheidung nach Severity

**Hinweis:** `drift_rate` ist ein diagnostischer Indikator. Er löst allein keine Gate-Entscheidung aus; die Severity-Verteilung der Findings bestimmt den Gate-Status.

---

## Kennzahl: retrieval_drift_rate

**Definition:** Anteil der Retrieval-Testqueries, deren Metrik-Delta die Warnschwelle überschreitet, an der Gesamtzahl ausgeführter Retrieval-Testqueries.

**Formel:**
```
retrieval_drift_rate = COUNT(queries WHERE metric_delta > warning_threshold) / COUNT(all_test_queries)
```

**Datenquelle:** Retrieval-Testquery-Ergebnisse vs. Golden Baseline (`drift_baseline.json`)

**Zielwert:** 0.0

**Warnschwelle:** > 0.05 (5 % der Queries über Schwelle) → RETRIEVAL_DRIFT error; Gate NO_GO

**Eskalation zu critical:** > 0.15 oder ≥ 3 aufeinander folgende Runs mit negativem Delta (Trendanalyse, siehe `drift_history_model.json`)

---

## Kennzahl: lifecycle_drift_rate

**Definition:** Anteil der Dokumente mit aktivem `lifecycle_status IN (archived, deleted)`, die trotzdem `is_searchable=true` oder im Index vorhanden sind.

**Formel:**
```
lifecycle_drift_rate = COUNT(documents WHERE lifecycle_status IN (archived, deleted) AND (is_searchable=true OR in_index=true)) / COUNT(documents WHERE lifecycle_status IN (archived, deleted))
```

**Datenquelle:** `documents` (PostgreSQL) + Search Index (read-only)

**Zielwert:** 0.0

**Warnschwelle:** > 0.0 — jeder Wert > 0 erzeugt mindestens ein `error`-Finding; Gate NO_GO.

**Hinweis:** Es gibt keine tolerierte Warnschwelle > 0 für diese Kennzahl. Jedes lifecycle-bereinigte Dokument, das suchbar bleibt, ist ein Integritätsbruch.

---

## Kennzahl: source_status_drift_rate

**Definition:** Anteil der registrierten Datenquellen eines Workspace mit `source_status=active`, die beim aktuellen Run nicht erreichbar oder als korrumpiert erkannt wurden.

**Formel:**
```
source_status_drift_rate = COUNT(data_sources WHERE source_status=active AND (unreachable=true OR corrupted=true)) / COUNT(data_sources WHERE source_status=active)
```

**Datenquelle:** `data_sources` (PostgreSQL) + Connectivity-Check (read-only)

**Zielwert:** 0.0

**Warnschwelle:** > 0.0 → Watch-Flag (wenn innerhalb Retry-Fenster); > konfigurierbarer Timeout → error; Gate NO_GO

---

## Metriken-Report-Mapping

| Kennzahl | Primärer Report | Sekundärer Report |
|----------|-----------------|------------------|
| total_checks | drift_report.json | drift_gate_report.json |
| total_drifts | drift_report.json | drift_summary.json |
| critical_drifts | drift_gate_report.json | drift_report.json |
| warning_drifts | drift_summary.json | drift_report.json |
| drift_rate | drift_summary.json | drift_history.json |
| retrieval_drift_rate | drift_report.json | drift_history.json |
| lifecycle_drift_rate | drift_gate_report.json | drift_summary.json |
| source_status_drift_rate | drift_summary.json | drift_report.json |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_metrics.schema.json` | Maschinenlesbares Schema |
| `drift_severity_matrix.json` | Severity-Schwellen |
| `drift_governance.schema.json` | Governance-Constraints |
| `schemas/drift_types.schema.json` | Typ-Autorität |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
