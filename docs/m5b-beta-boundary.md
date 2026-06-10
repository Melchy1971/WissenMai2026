# M5b Drift Detection — Beta Implementation Boundary

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt bis Implementation Gate GO).

---

## Voraussetzung

Diese Boundary gilt für M5b Beta. Beta ist erst erlaubt nach:
1. M5b Alpha Validation PASS
2. M5b Beta Start Gate PASS (siehe `reports/current/m5b_beta_start_gate.json`)

Aktueller Stand: M5b Alpha Validation **BLOCKED** (`reports/current/m5b_alpha_validation_report.json`). Beta ist nicht erlaubt.

---

## Erlaubter Beta-Scope

### Erlaubt

| Komponente | Beschreibung | Constraint |
|------------|--------------|-----------|
| Read-only Drift API | GET-Endpoints gemäß `docs/m5b-drift-api-scope.md` | Keine mutierenden Endpoints |
| Read-only Drift Dashboard | Widgets gemäß `docs/m5b-drift-dashboard-scope.md` | Keine Repair-/Cleanup-Buttons |
| CLI Runner | `python scripts/run_drift_detection.py --workspace <id>` | Nur Read-Zugriff auf PostgreSQL; schreibt Reports |
| Drift Reports | `drift_report.json`, `drift_summary.json`, `drift_gate_report.json` | Nur in `reports/current/` gemäß PROHIBIT-08 |
| Drift Metrics | Berechnung der 8 Metriken aus `drift_metrics.schema.json` | Keine automatische Gate-Aktion |
| Domain Model | PostgreSQL-Tabellen für DriftRun, DriftFinding, DriftSnapshot | Nur eigene Drift-Tabellen; keine Mutation an Document/Chunk-Tabellen |
| Alembic Migration | Migration für Drift-Tabellen | Keine Änderung bestehender Migrations |

### Nicht erlaubt

| Aktion | Begründung |
|--------|-----------|
| Repair-Aktionen | PROHIBIT-06 |
| Cleanup-Aktionen | PROHIBIT-02/03 |
| Reindex | PROHIBIT-03 |
| Lifecycle-Änderungen (`lifecycle_status`) | PROHIBIT-01 |
| `is_searchable` schreiben | PROHIBIT-02 |
| Metadata-Änderungen | PROHIBIT-04 |
| Auto-Close von Findings | PROHIBIT-05 |
| Cross-Workspace-Queries | PROHIBIT-07 |
| Schreiben außerhalb `reports/current/` + Drift-Tabellen | PROHIBIT-08 + Scope |
| M5c-Komponenten | Separates Gate erforderlich |
| Embeddings, Vektorsuche | Außerhalb V1-Scope |
| Agenten, automatische Korrekturen | Gate-Verletzung |

---

## PostgreSQL-Zugriffsmuster

Der Drift Detector liest ausschließlich. Erlaubte Zugriffe:

| Tabelle | Zugriff | Erlaubt |
|---------|---------|---------|
| `documents` | SELECT | ja |
| `document_versions` | SELECT | ja |
| `document_chunks` | SELECT | ja |
| `data_sources` | SELECT | ja |
| `drift_runs` | SELECT + INSERT (nur eigene Runs) | ja |
| `drift_findings` | SELECT + INSERT (nur eigene Findings) | ja |
| `drift_snapshots` | SELECT + INSERT (nur eigene Snapshots) | ja |
| `documents.lifecycle_status` | UPDATE | **nein** |
| `document_chunks.is_searchable` | UPDATE | **nein** |
| `data_sources.source_status` | UPDATE | **nein** |

---

## Report-Schreibzugriff

| Pfad | Erlaubt |
|------|---------|
| `reports/current/drift_report.json` | ja |
| `reports/current/drift_summary.json` | ja |
| `reports/current/drift_gate_report.json` | ja |
| `reports/current/drift_history.json` | ja |
| `reports/current/` (andere Reports) | **nein** (PROHIBIT-08) |
| `reports/archive/` | ja (nur Append) |

---

## Invarianten (unveränderlich)

- Drift Detection erkennt, korrigiert nie.
- Kein Beta-Artefakt darf eine der 8 PROHIBIT-Regeln aus `drift_governance.schema.json` verletzen.
- `remediation_hint` darf keine automatische Aktion implizieren (keine Imperativverben als ausführbare Befehle).
- `drift_id` ist stabil für (workspace_id, entity_type, entity_id, drift_type).
- Workspace-Isolation: kein Finding aus einem fremden Workspace.

---

## Gate-Abhängigkeit

| Gate | Voraussetzung für |
|------|------------------|
| Implementation Gate GO | Alpha-Implementierung |
| Alpha Validation PASS | Beta Start Gate |
| Beta Start Gate PASS | Beta-Implementierung |
| Beta Validation PASS | M5b Release Decision |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_governance.schema.json` | PROHIBIT-Regeln (verbindlich) |
| `docs/m5b-drift-api-scope.md` | API-Scope für Beta |
| `docs/m5b-drift-dashboard-scope.md` | Dashboard-Scope für Beta |
| `reports/current/m5b_implementation_gate.json` | Gate-Authority |
| `reports/current/m5b_beta_start_gate.json` | Beta-Freigabe-Gate |
