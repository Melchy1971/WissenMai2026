# M5c Cleanup Dashboard Scope

**Status:** DEFINITION  
**Datum:** 2026-06-12  
**Invariante:** Dashboard ist read-only — keine Execute/Delete/Merge Buttons

---

## Zweck

Das M5c Cleanup Dashboard visualisiert Dry-Run-Ergebnisse für manuelle Entscheidungen. Es ist ein reines Anzeige-Interface. Alle Aktionen außer Navigation sind deaktiviert.

---

## Verbotene UI-Elemente

Folgende Buttons und Interaktionen sind im Dashboard **nicht** erlaubt:

| Verboten | Grund |
|----------|-------|
| Execute-Button | Würde Proposals ausführen (außerhalb M5c-Scope) |
| Delete-Button | Würde Dokumente/Entitäten löschen (PROHIBIT-04) |
| Merge-Button | Würde Duplikate zusammenführen (PROHIBIT-05) |
| Repair-Button | Würde Daten korrigieren (PROHIBIT-02) |
| Cleanup-Button | Würde Cleanup auslösen (PROHIBIT-06) |
| Bulk-Action-Dropdown | Verhindert Massen-Aktionen |
| Approve-All-Button | Kein One-Click-Approval für Proposals |

---

## Widget 1: Candidate Count

**Typ:** KPI-Karte  
**Datenquelle:** `CleanupRun.candidates_found`

Anzeige:
- Gesamtzahl der Kandidaten im letzten Dry Run
- Vergleich zum vorherigen Run (Delta, keine Aktion)
- Aufschlüsselung nach Klasse: LOW / MEDIUM / HIGH / VERY_HIGH / CRITICAL

**Interaktion:** Keine. Read-only.

---

## Widget 2: Risk Breakdown

**Typ:** Balkendiagramm oder Donut-Chart  
**Datenquelle:** `CleanupRun.risk_summary.by_class`

Anzeige:
- Verteilung der Risk-Klassen als Prozentanteil
- Farbkodierung: LOW=grün, MEDIUM=gelb, HIGH=orange, VERY_HIGH=rot, CRITICAL=dunkelrot
- Durchschnittlicher Risk Score + Maximum

**Interaktion:** Klick auf Klasse → filtert Widget 4 (Candidate Table). Kein Schreibzugriff.

---

## Widget 3: Candidate Types

**Typ:** Gruppenbalken oder Tabelle  
**Datenquelle:** `CleanupRun.risk_summary.by_type`

Anzeige:
- Kandidaten-Anzahl je Typ: DUPLICATE_DOCUMENT, DUPLICATE_VERSION, ORPHAN_CHUNK, ORPHAN_VERSION, ORPHAN_CITATION, UNUSED_METADATA
- Prozentualer Anteil am Gesamtpool

**Interaktion:** Klick auf Typ → filtert Widget 4. Kein Schreibzugriff.

---

## Widget 4: Candidate Table

**Typ:** Datentabelle mit Paginierung  
**Datenquelle:** `cleanup_candidates` (für aktiven Run)

Spalten:
| Spalte | Beschreibung |
|--------|-------------|
| `candidate_type` | Typ-Label |
| `entity_type` | Betroffene Entität |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `risk_score` | 0–100 |
| `reason` | Erklärender Text |
| `remediation_hint` | Informationstext (kein Button) |
| `detected_at` | Zeitstempel |

Filter: Nach `candidate_type`, `severity`, `risk_score`-Range  
Sortierung: Nach `risk_score` DESC (default)  
Export: CSV (read-only Export erlaubt)

**Interaktion:** Nur Filtern, Sortieren, Paginieren, CSV-Export. Keine Aktionsbuttons.

---

## Widget 5: Dry Run History

**Typ:** Zeitreihe / Tabelle  
**Datenquelle:** `cleanup_audit` (historische Runs)

Anzeige:
- Liste vergangener Dry Runs: run_id, timestamp, candidate_count, avg_risk_score
- Trend: Kandidaten-Anzahl über Zeit (Liniendiagramm)
- Status-Spalte: COMPLETED / FAILED

**Interaktion:** Klick auf Run → lädt Snapshot in Widget 4 (historische Ansicht). Kein Schreibzugriff.

---

## data-testid Anforderungen

Jedes Widget muss folgende `data-testid`-Attribute exponieren:

| Widget | data-testid |
|--------|------------|
| Candidate Count Card | `cleanup-candidate-count` |
| Risk Breakdown Chart | `cleanup-risk-breakdown` |
| Candidate Types Chart | `cleanup-candidate-types` |
| Candidate Table | `cleanup-candidate-table` |
| Dry Run History | `cleanup-dry-run-history` |
| — | `cleanup-no-execute-button` (assert: nicht vorhanden) |
| — | `cleanup-no-delete-button` (assert: nicht vorhanden) |
| — | `cleanup-no-merge-button` (assert: nicht vorhanden) |

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt |
