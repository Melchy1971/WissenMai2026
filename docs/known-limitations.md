# Bekannte Einschraenkungen

Stand: 2026-06-15
Quelle: `reports/current/known_limitations.json`

**BLOCKING_CORE: 0** — Keine Limitation mit Release-Blockier-Status.

---

## Hohe Prioritaet (non-blocking)

### KL-M5-T-001 — M5 Entropy-/Drift-Truth-Failures

**Severity:** high | **Classification:** non_blocking
**Beschreibung:** M5 Entropy- und Drift-Truth-Failures in Backend-Tests blockieren den Start einzelner M5-Slices, nicht den RC.
**Status:** Dokumentiert. Unabhaengig vom Navigation- oder Frontend-Gate.

### KL-M5-T-002 — Drei Pflicht-Artefakte pro M5-Slice fehlen

**Severity:** high | **Classification:** non_blocking
**Beschreibung:** Je M5-Slice werden 3 Pflichtartefakte vor Slice-Start benoetigt. Gilt fuer M5c (Cleanup — NO-GO).
**Status:** Dokumentiert. M5c nicht gestartet.

### KL-GOV-001 — Mutierende Admin-Aktionen ohne Runbook gesperrt

**Severity:** high | **Classification:** non_blocking
**Beschreibung:** PROHIBIT-02, PROHIBIT-06, PROHIBIT-08: Repair, Cleanup, Auto-Execution ohne PO-Approval sind gesperrt.
**Status:** Aktiv. Governance-Grenze eingehalten.

---

## Niedrige Prioritaet

### KL-DEF-001 — OCR fuer gescannte PDFs

**Severity:** low | **Classification:** non_blocking
**Beschreibung:** OCR-Verarbeitung fuer reine Bild-PDFs ist kein V1-Bestandteil.
**Status:** Future phase.

### KL-DEF-002 — Embeddings und Vektorsuche optional

**Severity:** low | **Classification:** non_blocking
**Beschreibung:** Embedding-basierte Suche ist optional, nicht V1-kritisch.
**Status:** Future phase.

### KL-NB-001 — API-Alias nicht durchgaengig verfuegbar

**Severity:** low | **Classification:** non_blocking
**Beschreibung:** API-Alias `/api/v1/documents` nicht in allen Endpunkten konsistent verfuegbar.
**Status:** Dokumentiert. Kein User-Impact im Frontend.

---

## Nicht-Einschraenkungen (klargestellt)

Die folgenden Punkte wurden als bekannte BLOCKED-Gaete eingestuft, sind aber **keine BLOCKING_CORE Limitations**:

- `TEST_DATABASE_URL` nicht gesetzt: Betrifft Gate-Tests, nicht den laufenden Betrieb
- `report_integrity_v2` BLOCKED: Betrifft den Gate-Lauf, nicht das System selbst
- External Env Gate NOT_RUN: Erlaubter Zustand, blockiert RC nicht

---

## Navigation-Abweichungen (RC-relevant, keine Limitations)

Diese Punkte sind als RC-Blocker in `reports/current/release_candidate_gate.json` erfasst, nicht als known_limitations:

- AppShell NAV_ITEMS nicht synchron mit Masterplan (4 Abweichungen)
- /admin/diagnostics ohne Router-seitigen Admin-Guard

Vollstaendige Gate-Findings: `reports/current/final_navigation_release_check.json`
