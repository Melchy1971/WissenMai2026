# M5b Drift Detection — Rollback Strategie

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `rollback_strategy.json`.

---

## Problem

Falls Drift Detection nach Implementierung fehlerhafte Ergebnisse erzeugt (False Positives, fehlerhafte Gate-Entscheidungen, Report-Korruption), muss jede Komponente einzeln und ohne Datenmutation deaktivierbar sein.

---

## Rollback-Hierarchie

Drei unabhängig deaktivierbare Komponenten:

| Komponente | Rollback-Mechanismus | Datenmutation nötig |
|-----------|---------------------|---------------------|
| Detector | Feature Flag | nein |
| Reporting | Feature Flag | nein |
| Gates | Gate-Override-Flag | nein |

Rollback ist kumulativ: Detector aus → Reporting läuft weiter auf letztem Report; Reporting aus → Gates lesen letzten bekannten Report; Gate aus → System operiert ohne Drift-Gate-Constraint.

---

## Rollback 1: Detector deaktivieren

**Zweck:** Drift-Scans werden nicht mehr ausgeführt. Keine neuen Reports werden erzeugt.

**Mechanismus:** Feature Flag `drift_detection_enabled=false` in Systemkonfiguration.

**Effekt:**
- Laufende Scans werden nach aktuellem Run abgebrochen (kein Mid-Run-Abbruch)
- Keine neuen DriftRuns werden gestartet
- `reports/current/` bleibt unverändert (letzter vollständiger Report bleibt stehen)
- History-Daten bleiben vollständig erhalten
- Keine Datenmutation in PostgreSQL

**Rückgängig machen:** Feature Flag auf `drift_detection_enabled=true` setzen.

---

## Rollback 2: Reporting deaktivieren

**Zweck:** Reports werden nicht mehr nach `reports/current/` geschrieben, auch wenn Scans laufen.

**Mechanismus:** Feature Flag `drift_reporting_enabled=false`.

**Effekt:**
- Scans können weiterhin laufen (wenn Detector aktiv)
- Findings werden nicht in Reports persistiert
- `reports/current/` bleibt auf letztem Stand eingefroren
- Gate-Validator liest weiterhin den eingefrorenen letzten Report
- Kein Datenverlust; Findings werden nur nicht publiziert

**Rückgängig machen:** Feature Flag auf `drift_reporting_enabled=true` setzen.

**Hinweis:** Reporting-Deaktivierung allein deaktiviert nicht den Detector. Für vollständigen Rollback beide Flags setzen.

---

## Rollback 3: Gates deaktivieren

**Zweck:** Drift-Gate-Entscheidungen werden ignoriert; System operiert ohne Drift-Gate-Constraint.

**Mechanismus:** Gate-Override-Flag `drift_gate_active=false` in `reports/current/m5b_gate_criteria.json` (Änderung durch autorisierten Operator; nicht automatisch).

**Effekt:**
- Gate-Validator wertet `drift_gate_report.json` nicht mehr aus
- M5b Drift Gate gilt als `BYPASSED` (explizit dokumentiert, kein stilles Überschreiben)
- Alle anderen Gates (M5a, andere M5b-Kriterien) bleiben aktiv
- Bypass-Eintrag wird in `reports/current/m5b_gate_criteria.json` protokolliert mit Timestamp und Operator-ID
- Keine Datenmutation in PostgreSQL

**Rückgängig machen:** Flag auf `drift_gate_active=true` setzen; Bypass-Eintrag bleibt im Audit-Trail erhalten.

**Einschränkung:** Gate-Bypass erfordert explizite Operator-Entscheidung und Dokumentation. Kein automatischer Bypass durch das System.

---

## Datenmutation-Invariante

Kein Rollback-Schritt erfordert oder erlaubt Datenmutation in PostgreSQL. Das schließt ein:

- Kein Setzen von `lifecycle_status`
- Kein Ändern von `is_searchable`
- Kein Löschen von Chunks oder Dokumenten
- Kein Reindex
- Kein Ändern von `source_status`

Rollback operiert ausschließlich über Konfigurationsflags und Report-Status. Die Datenbasis bleibt unberührt.

---

## Rollback-Szenarien

| Fehlerbild | Empfohlener Rollback | Stufe |
|------------|---------------------|-------|
| Detector erzeugt Findings bei bekannt-korrekten Daten (False Positives) | Rollback 1: Detector aus | 1 |
| Reports enthalten inkonsistente oder korrumpierte Daten | Rollback 2: Reporting aus | 2 |
| Gate blockiert fälschlicherweise trotz bekannt-korrektem Zustand | Rollback 3: Gate aus | 3 |
| Alle drei Probleme gleichzeitig | Rollback 1 + 2 + 3 | kumulativ |

---

## Audit-Trail

Jede Rollback-Aktivierung wird protokolliert:

| Protokolleintrag | Inhalt |
|-----------------|--------|
| `component` | `detector`, `reporting`, `gate` |
| `action` | `disabled`, `enabled` |
| `timestamp` | ISO 8601 |
| `operator_id` | Identifier des Operators |
| `reason` | Freitext; Pflicht |

Audit-Trail ist unveränderlich; kein Eintrag wird gelöscht.

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `rollback_strategy.json` | Maschinenlesbares Schema |
| `drift_governance.schema.json` | PROHIBIT-Regeln (keine Datenmutation) |
| `reports/current/m5b_gate_criteria.json` | Gate-Override-Ziel |
| `docs/m5b-drift-governance.md` | Governance-Constraints |
