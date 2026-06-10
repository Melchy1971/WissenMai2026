# Known Limitations

Stand: 2026-06-10
Quelle: `reports/current/known_limitations.json`

> Aktuelle Gate- und Freigabeaussagen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet.
> Manuelle Statusaussagen in diesem Dokument sind nicht autoritativ.

## Summary

| Total | Open | Deferred | Non-blocking | Blocking |
|---:|---:|---:|---:|---:|
| 6 | 3 | 3 | 6 | 0 |

## Gate-Scope-Regel

M5a ist nur dann durch Known Limitations blockiert, wenn eine offene Limitation `target_phase=M5A` hat und `blocks_gate` effektiv true ist. Das aktuelle Register enthaelt keine M5a-blockierende Limitation; M5a bleibt ausschliesslich durch die in `reports/current/m5a_final_readiness_review.json` genannten Eingangsreports blockiert.

M5b `DRAFT` und Architekturplanung erlauben keine Implementierung. `PREPARED` erlaubt Vorbereitung ohne Implementierung. Nur `GO` in `reports/current/m5b_release_decision.json` erlaubt M5b Implementierung.

## Limitations nach Zielphase

### M5B_IMPL

#### KL-M5-T-001 - M5 Entropy-/Drift-Truth-Failures blockieren Slice-Start

| Field | Value |
|---|---|
| Status | `open` |
| Severity | `high` |
| Category | spätere M5b Implementierung |
| Target Phase | `M5B_IMPL` |
| Blocks Gate | `[]` |
| Evidence | `reports/current/pre_m5_decision_report.json` |
| Owner | `m5_truth_owner` |

**Beschreibung:** M5 Entropy-/Drift-Truth ist weiterhin nicht freigegeben: reports/current/m4_truth_report.json ist PASS, schliesst M5-Governance aber explizit aus; ein aktueller gruener M5-Truth-Block fehlt. Diese Limitation blockiert nicht das M5a Parent-Gate; sie bleibt eine spaetere M5b-Implementierungs-/Slice-Aktivierungs-Voraussetzung.

**Naechste Aktion:** Nicht als M5a-Final-Readiness-Blocker zaehlen. Vor spaeterer M5b-Implementierung oder Slice-Aktivierung aktuellen M5-Truth-Nachweis erzeugen: pytest --pg tests/truth/m5/ ausfuehren, daraus m5_truth_report artifact mit status=PASS, failed=0, errors=0, blockers=[] generieren und erst danach die jeweilige Implementierungsfreigabe bewerten.

#### KL-M5-T-002 - Drei Pflicht-Artefakte pro M5-Slice fehlen vor Slice-Start

| Field | Value |
|---|---|
| Status | `open` |
| Severity | `high` |
| Category | spätere M5b Implementierung |
| Target Phase | `M5B_IMPL` |
| Blocks Gate | `[]` |
| Evidence | `reports/current/m5b_release_decision.json` |
| Owner | `m5_slice_owner` |

**Beschreibung:** Die fehlenden Slice-Artefakte betreffen die spaetere M5b-Implementierungsfreigabe, nicht Report Integrity, nicht das M5a Data Quality Gate und nicht das M5b Start-Gate. Die aktuelle Evidence verweist auf M5b Drift/Retrieval-Readiness: Retrieval-Baseline ist WARN/nicht release-grade, M5b Drift Architecture ist DRAFT, und Cleanup-Dry-Run sowie passende PostgreSQL-Truth-Bloecke bleiben spaetere Implementierungsnachweise.

**Naechste Aktion:** Nicht als aktuelles Gate-Blocking zaehlen. Fuer spaetere M5b-Implementierung: reports/current/retrieval_quality_baseline_report.json auf release-grade PASS bringen, M5b Drift Architecture von DRAFT auf freigegeben bringen, Cleanup-Dry-Run-Report mit blocked_count=0 erzeugen, passenden M5b-Truth-Block PASS/GO nachweisen und danach ein eigenes m5b_implementation_gate bewerten.

### GOVERNANCE

#### KL-GOV-001 - Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt

| Field | Value |
|---|---|
| Status | `deferred` |
| Severity | `high` |
| Category | Governance/Operations allgemein |
| Target Phase | `GOVERNANCE` |
| Blocks Gate | `[]` |
| Evidence | `docs/m4d-admin-diagnostics.md` |
| Owner | `operations_owner` |

**Beschreibung:** Mutierende Admin-Aktionen (Repair, Cleanup-Loeschen, forced Reindex, Restore/Backfill-Ausfuehrung) sind nicht Teil von M5a und nicht Voraussetzung fuer M5b Preparation oder nicht-mutierende M5b Implementation. M5a bleibt read-only Data Quality und fuehrt keine Repair-/Cleanup-Aktionen aus; KL-GOV-001 blockiert daher kein aktuelles M5a- oder M5b-Gate. Jede spaetere mutierende Adminaktion braucht vor Freigabe ein eigenes Runbook, Dry-Run, Audit-Regel und operational_governance_gate.

**Naechste Aktion:** Keine M5a-Readiness, M5b-Preparation oder nicht-mutierende M5b-Implementation durch KL-GOV-001 blockieren. Erst wenn Repair, Cleanup-Loeschen, forced Reindex, Restore/Backfill oder aehnliche Web-Admin-Mutationen ausgefuehrt werden sollen: dediziertes Runbook, Dry-Run-Nachweis, Auth-/Redaction-/Audit-/Failure-Tests und operational_governance_gate positiv nachweisen.

### M5C_PLUS

#### KL-DEF-001 - OCR fuer gescannte PDFs nicht Teil von V1

| Field | Value |
|---|---|
| Status | `deferred` |
| Severity | `low` |
| Category | non-blocking technical debt |
| Target Phase | `M5C_PLUS` |
| Blocks Gate | `[]` |
| Evidence | `masterplan.md` |
| Owner | `product_owner` |

**Beschreibung:** OCR fuer gescannte PDFs ist nicht Teil von V1. PDFs ohne extrahierbaren Text bleiben OCR_REQUIRED.

**Naechste Aktion:** OCR als eigenes Feature-Paket konzipieren und priorisieren.

#### KL-DEF-002 - Embeddings und Vektorsuche optional und nicht V1-kritisch

| Field | Value |
|---|---|
| Status | `deferred` |
| Severity | `low` |
| Category | non-blocking technical debt |
| Target Phase | `M5C_PLUS` |
| Blocks Gate | `[]` |
| Evidence | `masterplan.md` |
| Owner | `architecture_owner` |

**Beschreibung:** Embeddings und Vektorsuche sind optional und nicht V1-kritisch.

**Naechste Aktion:** FTS-Baseline weiter nutzen; Vektorsuche separat konzipieren.

#### KL-NB-001 - API-Alias /api/v1/documents nicht durchgaengig verfuegbar

| Field | Value |
|---|---|
| Status | `open` |
| Severity | `low` |
| Category | non-blocking technical debt |
| Target Phase | `M5C_PLUS` |
| Blocks Gate | `[]` |
| Evidence | `docs/api.md` |
| Owner | `api_owner` |

**Beschreibung:** Der Alias /api/v1/documents ist nicht durchgaengig verfuegbar; Pfade nutzen teilweise /documents.

**Naechste Aktion:** Vor neuer Clientbindung API-Vertrag pruefen; Alias oder Routing konsolidieren.

## Documentation Truth Lint

Aktueller Nachweis: `reports/current/documentation_truth_lint.json`.

