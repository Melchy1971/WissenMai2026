# M5 Drift Detection

Stand: 2026-06-10

## Status

- Phase: DRAFT — Planungsartefakte vollstaendig (Stand 2026-06-10)
- Implementierung: **nicht gestartet, NO-GO** (siehe `reports/current/m5b_implementation_gate.json`)
- Formales PREPARED: BLOCKED (M5a READY_FOR_M5B und Report Integrity fehlen)
- Drift Detection Code: nicht vorhanden
- Repair Code: nicht vorhanden; kein Repair-Scope in M5b
- Freigabestatus: kein produktiver Betrieb bis Implementation Gate explizit PASS/GO
- Drift Detection bleibt read-only; keine Repair-Aktionen in M5b

> **Authoritative Drift-Typen:** Die nachfolgende alte Drift-Typen-Tabelle (6 Typen) ist konzeptioneller Vorlaeufер. Die finale Typdefinition mit 7 Typen befindet sich in `docs/m5b-drift-types.md` und `schemas/drift_types.schema.json`.
> Bekannte Risiken: `docs/m5b-risk-matrix.md`

---

## Scope

- DB vs. Search Index
- Lifecycle vs. Suchbarkeit
- Citation Snapshot vs. Live-Status
- Queue State vs. tatsächlicher Worker-Zustand
- Backup Manifest vs. aktuelle Daten
- Retrieval-Qualität über Zeit

---

## Drift-Arten und Bewertungslogik

| Drift-Art | Primärquelle | Erkennungslogik | Severity |
|---|---|---|---|
| `db_index_divergence` | DB-Chunks vs. Search-Index | Count-Differenz je Workspace | `error` wenn > 0 nach Reindex |
| `lifecycle_searchability` | `lifecycle_status` vs. Index-Präsenz | archivierte/gelöschte Docs ohne Index-Austragung | `error` |
| `citation_snapshot_drift` | Citation-Snapshot vs. Chunk-Content-Hash | Abweichung Snapshot vs. Live-Chunk | `warning`/`error` je Fall |
| `queue_worker_divergence` | `background_jobs.status` vs. Worker-Heartbeat | `running`-Jobs ohne aktiven Worker nach Timeout | `warning`/`error` |
| `backup_manifest_drift` | Backup-Manifest vs. aktuelle DB-Cardinality | Zeilen-/Chunk-Differenz | `warning`/`error` je Abweichung |
| `retrieval_quality_drift` | Retrieval-Benchmark vs. Golden Baseline | Metrik-Delta > 0.05 gegen Baseline | `error` |

---

## Schwellen

| Drift-Art | Stop-Kriterium | Warnschwelle |
|---|---|---|
| `db_index_divergence` | stale_index_growth > 0 nach Reindex | > 0 außerhalb Wartungsfenster |
| `lifecycle_searchability` | Lifecycle-Exclusion-Violations > 0 | — |
| `citation_snapshot_drift` | historische Citation fehlt | Snapshot-Hash-Abweichung |
| `queue_worker_divergence` | persistente Divergenz nach 2x Timeout | Jobs älter als Timeout |
| `backup_manifest_drift` | Restore-Verifikation fehlgeschlagen | Cardinality-Abweichung |
| `retrieval_quality_drift` | Baseline-Delta > 0.05 | negative 7d-Bewegung |

---

## Drift Score

Gewichtete Aggregation aller aktiven Drift-Arten. Wert 0 = kein Drift. Wert > 0 außerhalb Wartungsfenster: `watch`. Persistenter Drift nach Repair: `blocked`.

Metrik-Definition: `backend/app/observability/m5_metrics.py` (`m5_drift_score`)

---

## Repair-Steuerung

Repair ist explizit ausgelöst, nie automatisch.

| Repair-Typ | Auslöser | Runbook |
|---|---|---|
| Reindex (workspace-scoped) | `db_index_divergence` oder `lifecycle_searchability` | `docs/runbooks/m5-drift-repair-strategy.md` |
| Citation-Snapshot-Repair | `citation_snapshot_drift` mit fehlenden Snapshots | `docs/runbooks/m5-drift-repair-strategy.md` |
| Queue-Recovery | `queue_worker_divergence` persistent | `docs/runbooks/m5-drift-repair-strategy.md` |
| Backup-Refresh | `backup_manifest_drift` mit gescheiterter Verifikation | `docs/runbooks/backup-restore.md` |

---

## Report-Format

```json
{
  "report_type": "drift_detection",
  "generated_at": "<iso8601>",
  "workspace_id": "<uuid>",
  "status": "ok | watch | blocked",
  "drift_score": 0.0,
  "findings": [
    { "drift_type": "db_index_divergence", "severity": "error", "count": 0 }
  ]
}
```

---

## Nicht-Scope

- Kein aktiver Reindex oder Repair ohne explizite Freigabe
- Keine automatische Snapshot-Korrektur
- Keine produktive Drift-Reparatur per Web-Admin

---

## Implementierungsanker (geplant; kein Code vorhanden)

- CLI (geplant): `python -m app.cli m5 drift-check --workspace <id>`
- Geplantes Report-Artefakt: `m5_drift_report.json`
- Repair-Strategie: ausserhalb M5b-Scope; kein Repair ohne separates Governance-Gate
- Truth-Test-Block: `drift_detection` (geplant; siehe `docs/m5b-test-strategy.md`)

---

## M5b Preparation-Referenzen (Stand 2026-06-10)

| Artefakt | Zweck |
|----------|-------|
| `docs/m5b-preparation-boundary.md` | Erlaubt/Verboten-Scope |
| `docs/m5b-drift-types.md` | Finale 7 Drift-Typen |
| `schemas/drift_types.schema.json` | Autoritative Typdefinition |
| `docs/m5b-gates.md` | Gate-Kriterien |
| `docs/m5b-test-strategy.md` | Teststrategie |
| `docs/m5b-risk-matrix.md` | Risikoanalyse |
| `reports/current/m5b_preparation_gate.json` | Preparation-Gate-Status |
| `reports/current/m5b_implementation_gate.json` | Implementation-Gate NO-GO |
| `docs/m5b-drift-governance.md` | Governance: Drift Detection darf nur erkennen, nie korrigieren |
| `drift_governance.schema.json` | JSON Schema: DriftFinding, alle Pflichtfelder, verbotene Operationen |
