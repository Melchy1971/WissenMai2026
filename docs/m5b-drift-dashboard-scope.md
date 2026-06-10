# M5b Drift Detection — Dashboard Minimal Scope

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

---

## Kernprinzip

Das Drift Dashboard ist ein read-only Beobachtungswerkzeug. Es zeigt den Zustand des letzten Drift Runs und die aktuelle Finding-Verteilung. Es enthält keine Repair-, Cleanup- oder Reindex-Buttons. Jede angezeigte Information stammt aus einer der vier Report-Typen (Quelle: `reporting_architecture.json`).

---

## Widgets

### W-01: Letzter Drift Run

| Feld | Quelle | Typ |
|------|--------|-----|
| `run_id` | `drift_report.json` | string (UUID) |
| `started_at` | `drift_report.json` | timestamp |
| `completed_at` | `drift_report.json` | timestamp |
| `workspace_id` | `drift_report.json` | string (UUID) |
| `status` | `drift_report.json` | `completed` / `failed` |

**Constraint:** Zeigt nur den letzten abgeschlossenen Run im aktuellen Workspace.

---

### W-02: Total Drifts

| Feld | Quelle | Typ |
|------|--------|-----|
| `total_drifts` | `drift_summary.json` | integer |
| `total_checks` | `drift_summary.json` | integer |
| `drift_rate` | `drift_summary.json` | float (0.0–1.0) |

**Berechnung:** `drift_rate = total_drifts / total_checks` (Quelle: `drift_metrics.schema.json`).

---

### W-03: Drift Rate

Visuelle Darstellung der `drift_rate` als Gauge oder Prozentzahl.

| Schwelle | Zustand |
|---------|---------|
| `drift_rate = 0.0` | Grün / OK |
| `drift_rate > 0.0 AND <= 0.1` | Gelb / Watch |
| `drift_rate > 0.1` | Rot / Alert |

**Constraint:** Keine automatische Aktion bei Überschreitung. Nur visuelle Kennzeichnung.

---

### W-04: Severity Breakdown

Verteilung der Findings nach Severity-Level.

| Anzeige | Quelle | Severity-Level |
|---------|--------|----------------|
| Info-Count | `drift_summary.json` | `info` |
| Warning-Count | `drift_summary.json` | `warning` |
| Error-Count | `drift_summary.json` | `error` |
| Critical-Count | `drift_summary.json` | `critical` |

**Binding Rule:** Warning-Count allein darf keinen Gate-Block-Hinweis erzeugen (Quelle: `drift_severity_matrix.json`, WARNING binding rule).

---

### W-05: Findings Table

Tabellarische Darstellung der Findings aus `drift_report.json`.

Pflichtfelder je Tabellenzeile:

| Spalte | Quelle | Typ |
|--------|--------|-----|
| `drift_id` | `drift_report.json` | string |
| `entity_type` | `drift_report.json` | enum (7 Typen) |
| `entity_id` | `drift_report.json` | string |
| `drift_type` | `drift_report.json` | enum (7 Typen) |
| `severity` | `drift_report.json` | enum (info/warning/error/critical) |
| `detected_at` | `drift_report.json` | timestamp |
| `remediation_hint` | `drift_report.json` | string (Freitext) |

**Sortierung:** Default `severity DESC, detected_at DESC`.

**Nicht erlaubte Spalten/Aktionen:** Kein Repair-Button, kein Dismiss-Button, kein Auto-Close-Button. `remediation_hint` ist reiner Freitext — kein klickbares Element, kein ausführbarer Link (Quelle: PROHIBIT-05 in `drift_governance.schema.json`).

---

### W-06: Drift Type Filter

Filter für die Findings Table (W-05).

| Filter-Dimension | Werte |
|-----------------|-------|
| `drift_type` | DOCUMENT_DRIFT, CHUNK_DRIFT, METADATA_DRIFT, LIFECYCLE_DRIFT, SOURCE_STATUS_DRIFT, SEARCH_INDEX_DRIFT, RETRIEVAL_DRIFT |
| `severity` | info, warning, error, critical |

**Constraint:** Filter operiert client-seitig auf den geladenen Findings des aktuellen Runs. Kein Cross-Workspace-Query (Quelle: PROHIBIT-07).

---

## Verbotene Dashboard-Elemente

| Element | Grund |
|---------|-------|
| Repair-Button | PROHIBIT-06: kein Repair Call |
| Cleanup-Button | PROHIBIT-02 / PROHIBIT-03: kein is_searchable write, kein Reindex |
| Auto-Dismiss Finding | PROHIBIT-05: kein Auto-Close |
| Workspace-übergreifende Anzeige | PROHIBIT-07: kein Cross-Workspace-Query |
| Live-Mutation von lifecycle_status | PROHIBIT-01 |
| Export in beschreibbare Quelle | n/a — Export ist read-only (PDF/CSV) |

---

## Workspace-Scoping

Das Dashboard zeigt ausschließlich Findings des aktiven Workspace. Die `workspace_id` stammt aus dem Auth-Kontext (nicht aus Query-Parametern). Kein Dropdown zur Workspace-Auswahl in der Findings Table.

---

## Datenquellen

| Widget | Report-Typ | Schema-Ref |
|--------|-----------|------------|
| W-01 | drift_report.json | `reporting_architecture.json` |
| W-02, W-03, W-04 | drift_summary.json | `reporting_architecture.json` |
| W-05, W-06 | drift_report.json | `drift_governance.schema.json` |

---

## Nicht-Scope

- Historische Run-Vergleiche (→ erst nach `drift_history.json` Implementierung)
- Trend-Charts über mehrere Runs
- Alert-/Notification-System
- Export-Funktion (spätere Erweiterung)
- Admin-Aktionen jeder Art

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `reporting_architecture.json` | Report-Typen und Pflichtfelder |
| `drift_governance.schema.json` | PROHIBIT-Regeln, Feldconstraints |
| `drift_severity_matrix.json` | Severity-Semantik und WARNING binding rule |
| `drift_metrics.schema.json` | Metrik-Formeln und Schwellenwerte |
| `dashboard_testids.md` | Test-IDs für alle Widgets |
