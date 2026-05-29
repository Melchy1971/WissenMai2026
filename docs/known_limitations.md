# Known Limitations

Stand: 2026-05-29
Quelle: `reports/current/known_limitations.json`

> Aktuelle Gate- und Freigabeaussagen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet.
> Manuelle Statusaussagen in diesem Dokument sind nicht autoritativ.

---

## Aktive Limitations

Gesamt: 6 | Aktiv: 4 | Behoben: 0

### KL-M5-T-001

**Status:** `open`  |  **Kategorie:** M5 blocker  |  **Zielphase:** M5

15 M5 Entropy-/Drift-Truth-Failures in aktueller PostgreSQL-Truth-Suite. Kein M5-Slice darf produktiv gehen, bevor sein Truth-Block gruen ist.

**Blocks Gate:** `m5_truth_gate`

**Workaround:** M5-Truth-Failures isoliert reparieren; pytest --pg tests/truth/m5/ -k <slice> ausfuehren; Slice erst nach gruenem Truth-Block aktivieren.

---

### KL-M5-T-002

**Status:** `open`  |  **Kategorie:** M5 blocker  |  **Zielphase:** M5

Vor Start jedes M5-Slices fehlen drei Pflicht-Artefakte: (1) Retrieval-Baseline, (2) Cleanup Dry-Run mit blocked_count=0, (3) PostgreSQL-Truth-Block gruen.

**Blocks Gate:** `m5_slice_start_gate`

**Workaround:** Slice-sequenziell: Truth-Block gruen → python -m app.cli m5 retrieval-benchmark --set-baseline → python -m app.cli m5 cleanup-dry-run --workspace <id>.

---

### KL-GOV-001

**Status:** `open`  |  **Kategorie:** operational governance  |  **Zielphase:** M5 Operations

Mutierende Admin-Aktionen (Repair, Cleanup-Loeschen, forced Reindex) duerfen nicht ueber Web-Admin ausgeloest werden. M4d bleibt read-only; operativer Mutationspfad braucht explizites Runbook und Freigabe.

**Blocks Gate:** `operational_governance_gate`

**Workaround:** Fuer jeden Mutationspfad eigenes Runbook schreiben. Runbook vor produktiver Nutzung freigeben. Keine Web-Admin-Buttons ohne Gate-Freigabe.

---

### KL-NB-001

**Status:** `open`  |  **Kategorie:** non-blocking debt  |  **Zielphase:** M4/M5 API hardening

Der Alias /api/v1/documents ist nicht durchgaengig verfuegbar; Pfade nutzen teilweise /documents.

**Blocks Gate:** —

**Workaround:** Vor neuer Clientbindung API-Vertrag pruefen; Alias oder Routing konsolidieren.

---

## Behobene Limitations

