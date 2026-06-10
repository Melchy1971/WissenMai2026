# M5b Drift Dashboard — Test IDs

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt).

Scope-Referenz: `docs/m5b-drift-dashboard-scope.md`

---

## Konvention

Format: `data-testid="drift-<widget>-<element>"`. Alle Test-IDs sind read-only. Kein Test-ID für mutierende Elemente (diese sind verboten).

---

## W-01: Letzter Drift Run

| Test-ID | Element |
|---------|---------|
| `drift-run-card` | Container des Run-Widgets |
| `drift-run-id` | Anzeige der run_id |
| `drift-run-started-at` | Anzeige started_at |
| `drift-run-completed-at` | Anzeige completed_at |
| `drift-run-workspace-id` | Anzeige workspace_id |
| `drift-run-status` | Status-Badge (completed/failed) |

---

## W-02: Total Drifts

| Test-ID | Element |
|---------|---------|
| `drift-total-card` | Container |
| `drift-total-drifts` | Zahl total_drifts |
| `drift-total-checks` | Zahl total_checks |
| `drift-total-rate` | Prozentwert drift_rate |

---

## W-03: Drift Rate

| Test-ID | Element |
|---------|---------|
| `drift-rate-gauge` | Gauge-Container |
| `drift-rate-value` | Numerischer Wert |
| `drift-rate-status-ok` | Grün-Zustand (rate = 0.0) |
| `drift-rate-status-watch` | Gelb-Zustand (0.0 < rate <= 0.1) |
| `drift-rate-status-alert` | Rot-Zustand (rate > 0.1) |

---

## W-04: Severity Breakdown

| Test-ID | Element |
|---------|---------|
| `drift-severity-breakdown` | Container |
| `drift-severity-info-count` | Anzahl info |
| `drift-severity-warning-count` | Anzahl warning |
| `drift-severity-error-count` | Anzahl error |
| `drift-severity-critical-count` | Anzahl critical |

---

## W-05: Findings Table

| Test-ID | Element |
|---------|---------|
| `drift-findings-table` | Tabellen-Container |
| `drift-findings-row` | Tabellenzeile (je Finding) |
| `drift-finding-id` | drift_id-Zelle |
| `drift-finding-entity-type` | entity_type-Zelle |
| `drift-finding-entity-id` | entity_id-Zelle |
| `drift-finding-drift-type` | drift_type-Zelle |
| `drift-finding-severity` | severity-Badge |
| `drift-finding-detected-at` | Timestamp-Zelle |
| `drift-finding-remediation-hint` | Hinweistext (read-only) |
| `drift-findings-empty` | Leer-State |

**Nicht vorhanden:** `drift-finding-repair-button`, `drift-finding-dismiss-button`, `drift-finding-action-*` — diese Elemente sind verboten.

---

## W-06: Drift Type Filter

| Test-ID | Element |
|---------|---------|
| `drift-filter-container` | Filter-Container |
| `drift-filter-type` | Drift-Type-Dropdown |
| `drift-filter-severity` | Severity-Dropdown |
| `drift-filter-reset` | Reset-Button |
| `drift-filter-type-option-{type}` | Je Drift-Type Option (7 Stück) |
| `drift-filter-severity-option-{level}` | Je Severity-Option (4 Stück) |

---

## Verboten (keine Test-IDs)

| Test-ID | Warum nicht vorhanden |
|---------|----------------------|
| `drift-repair-button` | PROHIBIT-06 |
| `drift-cleanup-button` | PROHIBIT-02/03 |
| `drift-reindex-button` | PROHIBIT-03 |
| `drift-dismiss-finding` | PROHIBIT-05 |
| `drift-workspace-switcher` | PROHIBIT-07 |
| `drift-auto-fix-*` | Alle PROHIBIT-Regeln |
