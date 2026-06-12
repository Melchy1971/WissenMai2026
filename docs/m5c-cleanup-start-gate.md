# M5c Cleanup Start Gate

**Status: BLOCKED**
Generiert: 2026-06-12
Basis: m5b_production_readiness_gate.json → decision=BLOCKED

---

## Zweck

Dieses Gate definiert die Voraussetzungen, unter denen M5c Cleanup beginnen darf.
Solange dieses Gate BLOCKED ist, findet keine Cleanup-Implementierung statt.

**Invariante:** Drift Detection darf nur erkennen, nie korrigieren. (PROHIBIT-02, PROHIBIT-06)

---

## Voraussetzungen (alle müssen PASS sein)

| ID | Voraussetzung | Aktueller Status |
|----|---------------|-----------------|
| SG-01 | M5b Production Readiness Gate PASS | **BLOCKED** |
| SG-02 | Alpha Hardening Gate PASS | **BLOCKED** |
| SG-03 | Drift Report Integrity PASS (kein PARTIAL) | **BLOCKED** |
| SG-04 | m5b_alpha_validation_report PASS | **BLOCKED** |
| SG-05 | Cleanup Governance Boundary ratifiziert | DRAFT |

---

## Aktuelle Blocker

### SG-01 / SG-02: Production Readiness BLOCKED
Ursache-Kette:
```
m5b_production_readiness_gate BLOCKED
  ← m5b_beta_validation_report BLOCKED (BV-07)
    ← m5b_alpha_hardening_gate BLOCKED
      ← AHG-BLOCKER-01: m5b_alpha_validation_report BLOCKED
        (AV-01: M5a READY_FOR_M5B nicht vorhanden oder report_integrity_v2 nicht PASS)
      ← AHG-BLOCKER-02: drift_report_integrity PARTIAL
        (drift_report.json + drift_summary.json noch nicht durch CLI-Run erzeugt)
```

### SG-05: Cleanup Governance Boundary
Definition existiert (cleanup_governance_boundary.json), aber kein ratifiziertes Gate-Dokument bis M5b PASS.

---

## Was in M5c Planung erlaubt ist

Nur Planungsdokumente ohne Implementierung:
- Cleanup-Strategie-Dokumente (kein ausführbarer Code)
- Dry-Run-Konzepte (kein Ausführen)
- Governance-Regeln definieren
- Rollback-Kriterien dokumentieren

## Was nicht erlaubt ist (ohne separates Gate)

- Jede DELETE / TRUNCATE / DROP Anweisung
- Automatisierte Cleanup-Jobs
- Repair-Actions in irgendeiner Form
- Auto-Reindex-Aktionen
- Ausführung von Cleanup-Code in Produktion oder Staging

---

## Aktivierungsbedingung

Das Gate wechselt von BLOCKED auf PASS wenn **alle** SG-01 bis SG-05 erfüllt sind.
Eine manuelle Freigabe durch den Product Owner ist zusätzlich erforderlich.
