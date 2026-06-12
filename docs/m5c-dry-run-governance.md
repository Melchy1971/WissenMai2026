# M5c Dry Run Governance

**Status:** DEFINITION  
**Datum:** 2026-06-12  
**Invariante:** Dry Run erzeugt ausschließlich Vorschläge — keine Datenänderung

---

## Definition

Ein Dry Run ist ein Cleanup-Analysedurchlauf, der:
- Kandidaten erkennt und bewertet
- Proposals generiert (status=PENDING)
- **keinerlei Daten verändert**
- als vollständiger Report persistiert wird

Jeder M5c-Run ist per Definition ein Dry Run. Es gibt keine "echte" Ausführung ohne expliziten PO-Sign-off auf jedes einzelne Proposal.

---

## Pflichtregeln

| Nr. | Regel | Verletzung führt zu |
|-----|-------|---------------------|
| DR-01 | Dry Run erzeugt nur Proposals (status=PENDING) | Run-Abbruch + FAILED-Status |
| DR-02 | Keine Datenänderung in `documents`, `chunks`, `citations`, `document_metadata` | Sofortiger Abbruch, Incident-Log |
| DR-03 | Keine Lifecycle-Änderung (lifecycle_status bleibt unverändert) | Run-Abbruch + FAILED-Status |
| DR-04 | Kein Löschen von Entitäten | Sofortiger Abbruch, CRITICAL-Alert |
| DR-05 | Kein Merge von Dokumenten oder Versionen | Run-Abbruch + FAILED-Status |
| DR-06 | Kein Reindex-Trigger (keine Änderungen am Vector-Index) | Run-Abbruch + FAILED-Status |

**DR-02 und DR-04 sind Hard-Stops:** Jede erkannte Verletzung terminiert den Prozess sofort mit `status=FAILED` und schreibt einen CRITICAL-Audit-Eintrag.

---

## Pflichtfelder eines Dry Run Reports

Jeder abgeschlossene Dry Run muss folgende Felder im Report haben:

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|-------------|
| `run_id` | UUID | ja | Eindeutige Run-ID |
| `timestamp` | ISO8601 | ja | Startzeitpunkt des Runs |
| `workspace_id` | UUID | ja | Workspace-Scope |
| `candidates` | array | ja | Vollständige Kandidatenliste |
| `risk_summary` | object | ja | Aggregierte Risk-Score-Verteilung |

### risk_summary Pflichtstruktur

```json
{
  "total": 42,
  "by_class": {
    "LOW":       10,
    "MEDIUM":    15,
    "HIGH":       8,
    "VERY_HIGH":  6,
    "CRITICAL":   3
  },
  "by_type": {
    "DUPLICATE_DOCUMENT": 5,
    "ORPHAN_CHUNK": 12
  },
  "max_risk_score": 94,
  "avg_risk_score": 38.2
}
```

---

## Sicherheitsmechanismus

Bevor ein Dry Run startet, prüft er:

1. **Pre-Check:** Keine offenen Proposals aus vorherigem Run (status=PENDING)
2. **DB-Constraint:** Write-Sperre auf `documents` für die Dauer des Runs (Advisory Lock, nicht Tabellensperre)
3. **Post-Check:** Hash-Vergleich der `documents`-Tabelle (Row-Count vor/nach muss identisch sein)

Schlägt der Post-Check fehl → `status=FAILED` + CRITICAL-Audit-Eintrag + manuelle Intervention erforderlich.

---

## Abgrenzung: Dry Run vs. Execution

| Aspekt | Dry Run (M5c Definition) | Execution (außerhalb M5c-Scope) |
|--------|--------------------------|----------------------------------|
| Proposals | PENDING | APPROVED → EXECUTED |
| Daten ändern | nein | ja (nach PO-Sign-off) |
| Automatisch | erlaubt | verboten |
| Review erforderlich | nein (für Run selbst) | Pflicht (je Proposal) |
| Aktueller Status | DEFINIERT | NOT IN SCOPE |

**Execution ist nicht Teil von M5c.** M5c definiert nur Detection, Dry Run und Reporting.

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt |
