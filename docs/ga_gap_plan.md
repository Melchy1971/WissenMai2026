# GA Gap Plan — Ruflo 1.0

Stand: 2026-06-16
Maschinenlesbare Quelle: `reports/current/ga_gap_plan.json`
Ziel: Von CONDITIONAL_RC (nach Sprint) zu GA / Version 1.0

---

## Aktueller Stand

| Metrik | Aktuell | RC-Minimum | GA-Minimum |
|--------|---------|-----------|------------|
| Product Maturity Score | 53 | 80 | 85 |
| Gold Path | 4/8 | 7/8 | 8/8 PASS |
| Technische ID Leaks | 0 | 0 | 0 |
| Blocking Security | 0 | 0 | 0 |
| Release Gate | BLOCKED | CONDITIONAL_RC | PASS |

**Aktuelle Entscheidung: BLOCKED** — RC und GA nicht erreichbar ohne Sprint-Completion.

---

## Pflichtbedingungen für GA

### GAT-01 — Product Maturity Score >= 85

Aktuell 53, Delta -32. Nach aktuellem Sprint erwartet 78–82.
Verbleibende Lücke bis GA: 3–7 Punkte nach Sprint.

Treiber nach Sprint:
- Tags-API vollständig → +5
- Lazy Loading → +8
- KWIC-Suche → +5
- Dashboard W06 Drift-Widget → +3

### GAT-02 — Gold Path 8/8 PASS

Aktuell 4/8. Schritte offen nach Sprint:

**GP-07 Export erzeugen** — bleibt CONDITIONAL_PASS nach Sprint (JSON/MD, kein PDF). Für GA-PASS: PDF-Export in 1.0 oder PO-Entscheidung, dass JSON/MD als vollständig gilt. Blockiert GA bis entschieden.

Alle anderen FAIL-Schritte (GP-04, GP-05, GP-06) sollen im aktuellen Sprint auf PASS gebracht werden.

### GAT-03 — Keine GA-blockierende Limitation

Aktuell 1 GA-Blocker: **RCL-01** (GP-07 CONDITIONAL_PASS, kein PDF). Fix: PDF-Export implementieren oder PO-Entscheidung GP-07 als PASS werten.

### GAT-04 — Sichtbare technische IDs = 0

Bereits erfüllt. `ui_technical_id_leak_audit.json`: leaks=0, PASS.

### GAT-05 — Product Release Gate PASS

Folgt automatisch aus GAT-01 bis GAT-03.

---

## Arbeitspaket-Plan

### GA-WP-01 — Topics-Backend abschließen (T09–T19, aktueller Sprint)
GP-04 → PASS. Fachlich +20, UX +15.

### GA-WP-02 — AnalysisPage.jsx vollständig (T25–T27, aktueller Sprint)
GP-05 und GP-06 → PASS. Fachlich +15, UX +15.
**Voraussetzung:** PO-Entscheidung zu Analyse-Schritten 5+7 vor Sprint-Start.

### GA-WP-03 — Export Center MVP + GA-Entscheidung (T28–T33, aktueller Sprint)
GP-07 → CONDITIONAL_PASS (JSON/MD). PDF für GA-PASS: 1.1 oder PO-Entscheidung.

### GA-WP-04 — Tags-API vollständig (POST + DELETE)
RCL-03 schließen. Fachlich +5. Sprint 1.0 oder 1.1.

### GA-WP-05 — Lazy Loading (Dokumente, Themen)
UX +8. Performance bei großen Datensätzen. Sprint 1.0 oder 1.1.

### GA-WP-06 — KWIC-Suche (Keyword in Context)
UX +5. Highlighting in Suchergebnissen. Sprint 1.0 oder 1.1.

### GA-WP-07 — Dashboard W06 Drift-Widget
RCL-02 schließen. UX +3. GET /api/v1/dashboard/drift + DriftWidget.jsx.

### GA-WP-08 — PO-Entscheidung GP-07 Export (sofort)
Bestimmt ob PDF nötig oder JSON/MD für GA ausreicht. Muss vor Sprint-Ende vorliegen.

---

## Phasenplan

**Phase 1 — Aktueller Sprint (T09–T33):**
Score ~78–82, Gold Path 7/8, CONDITIONAL_RC möglich.

**Phase 2 — GA-Arbeitspakete (WP-04 bis WP-08):**
Score 83–86, Gold Path 8/8 (nach GP-07-Entscheidung), GA erreichbar.

---

## Offene PO-Entscheidungen

| ID | Frage | Dringlichkeit |
|----|-------|---------------|
| PO-D01 | JSON/MD-Export ausreichend für CONDITIONAL_RC? | Vor Sprint-Ende |
| PO-D02 | Analyse-Schritte 5+7: konkrete Anforderungen? | Vor Sprint-Start |
| PO-D03 | PDF-Export in 1.0 oder PO-Freigabe GP-07 als GA-ausreichend? | Bei CONDITIONAL_RC-Entscheidung |

---

## Nicht im GA-Plan

- M5c Cleanup-Implementierung: **NO_GO** bis m5c_start_gate=PASS und PO-Sign-off (PROHIBIT-02, PROHIBIT-06)
- Repair-/Cleanup-Funktionen: **NO_GO** (KL-GOV-001)
- Automatische M5c-Ausführung: **NO_GO** ohne PO-Approval je Proposal (PROHIBIT-08)
