# Known Limitations

Generated: 2026-06-05T10:00:00+00:00  
Source: `reports/current/known_limitations.json`  
Authority: Nur maschinenlesbare Reports sind autoritativ. Manuelle Statusaussagen in dieser Datei duerfen keinen Gate-Status setzen.

## Summary

| Total | Open | Deferred | Non-blocking | Blocking |
|-------|------|----------|--------------|---------|
| 6 | 3 | 2 | 1 | 3 |

## M5 Blocker

### KL-M5-T-001 — M5 Entropy-/Drift-Truth-Failures blockieren Slice-Start **[BLOCKING]**

| Field | Value |
|-------|-------|
| Status | `open` |
| Category | M5 blocker |
| Target Phase | M5 |
| Blocks Gate | `m5_truth_gate` |
| Evidence | `reports/current/m4_truth_report.json` |

**Description:** 15 M5 Entropy-/Drift-Truth-Failures in aktueller PostgreSQL-Truth-Suite. Kein M5-Slice darf produktiv gehen, bevor sein Truth-Block gruen ist.

**Next Action:** M5-Truth-Failures isoliert reparieren; pytest --pg tests/truth/m5/ -k <slice> ausfuehren; Slice erst nach gruenem Truth-Block aktivieren.

### KL-M5-T-002 — Drei Pflicht-Artefakte pro M5-Slice fehlen vor Slice-Start **[BLOCKING]**

| Field | Value |
|-------|-------|
| Status | `open` |
| Category | M5 blocker |
| Target Phase | M5 |
| Blocks Gate | `m5_slice_start_gate` |
| Evidence | `docs/m5-preparation.md` |

**Description:** Vor Start jedes M5-Slices fehlen drei Pflicht-Artefakte: (1) Retrieval-Baseline, (2) Cleanup Dry-Run mit blocked_count=0, (3) PostgreSQL-Truth-Block gruen.

**Next Action:** Slice-sequenziell: Truth-Block gruen -> python -m app.cli m5 retrieval-benchmark --set-baseline -> python -m app.cli m5 cleanup-dry-run --workspace <id>.

## Operational Governance

### KL-GOV-001 — Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt **[BLOCKING]**

| Field | Value |
|-------|-------|
| Status | `open` |
| Category | operational governance |
| Target Phase | M5 Operations |
| Blocks Gate | `operational_governance_gate` |
| Evidence | `docs/m4d-admin-diagnostics.md` |

**Description:** Mutierende Admin-Aktionen (Repair, Cleanup-Loeschen, forced Reindex) duerfen nicht ueber Web-Admin ausgeloest werden. M4d bleibt read-only; operativer Mutationspfad braucht explizites Runbook und Freigabe.

**Next Action:** Fuer jeden Mutationspfad eigenes Runbook schreiben. Runbook vor produktiver Nutzung freigeben. Keine Web-Admin-Buttons ohne Gate-Freigabe.

## Non-Blocking Debt

### KL-NB-001 — API-Alias /api/v1/documents nicht durchgaengig verfuegbar 

| Field | Value |
|-------|-------|
| Status | `open` |
| Category | non-blocking debt |
| Target Phase | M4/M5 API hardening |
| Blocks Gate | — |
| Evidence | `docs/api.md` |

**Description:** Der Alias /api/v1/documents ist nicht durchgaengig verfuegbar; Pfade nutzen teilweise /documents.

**Next Action:** Vor neuer Clientbindung API-Vertrag pruefen; Alias oder Routing konsolidieren.

## Explicitly Deferred

### KL-DEF-001 — OCR fuer gescannte PDFs nicht Teil von V1 

| Field | Value |
|-------|-------|
| Status | `deferred` |
| Category | explicitly deferred |
| Target Phase | Post-M4 feature |
| Blocks Gate | — |
| Evidence | `masterplan.md` |

**Description:** OCR fuer gescannte PDFs ist nicht Teil von V1. PDFs ohne extrahierbaren Text bleiben OCR_REQUIRED.

**Next Action:** OCR als eigenes Feature-Paket konzipieren und priorisieren.

### KL-DEF-002 — Embeddings und Vektorsuche optional und nicht V1-kritisch 

| Field | Value |
|-------|-------|
| Status | `deferred` |
| Category | explicitly deferred |
| Target Phase | Post-V1 or M5+ |
| Blocks Gate | — |
| Evidence | `masterplan.md` |

**Description:** Embeddings und Vektorsuche sind optional und nicht V1-kritisch.

**Next Action:** FTS-Baseline weiter nutzen; Vektorsuche separat konzipieren.

---

## Evaluation Basis

| Gate | Status | Decision |
|------|--------|---------|
| M3a RC | `PASS` | `GO` |
| M4 Backend RC | `PASS` | `GO` |
| M4e Operations | `PASS` | `GO` |
| Doc Lint Errors | `0` | — |
