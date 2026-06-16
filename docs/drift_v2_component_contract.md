# Drift v2 Component Contract

Stand: 2026-06-15
Version: 1.0
Authority: PO (Markus Dickscheit)
Quelle: `frontend/src/features/drift_v2/DriftDashboard.jsx`

---

## Geltungsbereich

Dieser Contract definiert die verbindlichen Anforderungen an alle Komponenten unter `frontend/src/features/drift_v2/`. Er ist maßgeblich für Testschreibung, Code-Reviews und Freigabeentscheidungen.

Abweichungen vom Contract sind Bugs — keine Architekturentscheidungen.

---

## Pflichtkomponenten

| # | Komponenten-Name | Datei (Soll) | Status |
|---|---|---|---|
| 1 | `DriftDashboard` | `drift_v2/DriftDashboard.jsx` | IMPLEMENTIERT |
| 2 | `DriftRunSummary` | innerhalb `DriftDashboard.jsx` (Subrender) | IMPLEMENTIERT |
| 3 | `DriftSeverityBreakdown` | innerhalb `DriftDashboard.jsx` (Subrender) | IMPLEMENTIERT |
| 4 | `DriftTypeBreakdown` | innerhalb `DriftDashboard.jsx` (Subrender) | IMPLEMENTIERT |
| 5 | `DriftFindingsTable` | innerhalb `DriftDashboard.jsx` (Subrender) | IMPLEMENTIERT |
| 6 | `DriftFilters` | innerhalb `DriftDashboard.jsx` (Subrender) | IMPLEMENTIERT |

---

## Pflicht data-testid

Jede der folgenden `data-testid`-Attribute muss im gerenderten DOM von `DriftDashboard` vorhanden sein, wenn Daten verfügbar sind.

| data-testid | Zweck | Implementierungsstatus |
|---|---|---|
| `drift-dashboard` | Root-Container der gesamten Drift-Ansicht | **MATCH** — vorhanden |
| `drift-run-summary` | Letzter Drift-Run (Datum, Run-ID, Ergebnis) | **GAP** — Implementierung nutzt `drift-last-run-widget` |
| `drift-severity-breakdown` | Aufschlüsselung nach Severity (Critical/Error/Warning/Info) | **GAP** — Implementierung nutzt `drift-severity-breakdown-widget` |
| `drift-type-breakdown` | Aufschlüsselung nach Drift-Typ | **GAP** — Implementierung nutzt `drift-type-breakdown-widget` |
| `drift-findings-table` | Tabelle der Einzelfunde | **MATCH** — vorhanden |
| `drift-filter-severity` | Filter-Dropdown: Severity | **MATCH** — vorhanden |
| `drift-filter-type` | Filter-Dropdown: Typ | **MATCH** — vorhanden |

---

## Delta: Contract vs. aktuelle Implementierung

3 testids weichen ab. Diese müssen in `DriftDashboard.jsx` korrigiert werden, bevor der Component-Contract-Test auf PASS läuft.

| Contract (Soll) | Implementierung (Ist) | Erforderliche Änderung |
|---|---|---|
| `drift-run-summary` | `drift-last-run-widget` | Rename `data-testid` in DriftDashboard.jsx |
| `drift-severity-breakdown` | `drift-severity-breakdown-widget` | Rename `data-testid` in DriftDashboard.jsx (Suffix `-widget` entfernen) |
| `drift-type-breakdown` | `drift-type-breakdown-widget` | Rename `data-testid` in DriftDashboard.jsx (Suffix `-widget` entfernen) |

**Achtung:** Eine Umbenennung dieser testids bricht bestehende Tests in `DriftDashboard.test.jsx`, die derzeit die alten Namen verwenden. Beide Dateien müssen synchron migriert werden.

---

## Verbotene Komponenten (PROHIBIT)

Die folgenden Komponenten und Button-Typen sind im Scope von `drift_v2/DriftDashboard` **vollständig verboten**.

| Komponente | Regel | Begründung |
|---|---|---|
| `RepairButton` | PROHIBIT-02 | M5c Cleanup ist NO_GO bis Start-Gate PASS und PO-Sign-off |
| `CleanupButton` | PROHIBIT-06 | M5c Cleanup ist NO_GO bis Start-Gate PASS und PO-Sign-off |
| `DeleteButton` | PROHIBIT-02 | Destruktive Aktion ohne freigegebenes Gate |
| `ReindexButton` | PROHIBIT-02 | Repair-Aktion ohne freigegebenes Gate |

Verbotsprüfung umfasst:
- Direkte Verwendung im JSX
- Transitive Imports aus Subkomponenten
- Buttons mit Text-Content "Reparieren", "Repair", "Cleanup", "Bereinigen", "Löschen", "Delete", "Reindex", "Neuindizieren"

---

## Invarianten

1. **Detect only:** DriftDashboard zeigt Drift-Funde an. Keine Write-Aktionen.
2. **PROHIBIT-02 aktiv:** Kein Repair-Button in irgendeiner Form.
3. **PROHIBIT-06 aktiv:** Kein Cleanup-Button in irgendeiner Form.
4. **Route-Herkunft:** DriftDashboard ist ausschließlich über `/drift` → `DriftPage` → `drift_v2/DriftDashboard` erreichbar. Kein direkter Import aus anderen Pages.
5. **Kein Import aus `features/drift`:** Alle Imports zeigen auf `features/drift_v2`.

---

## Contract-Test

Maschinell validiert durch:
`frontend/src/tests/features/DriftV2ComponentContract.test.jsx`

Der Contract-Test ist die einzige autoritative Prüfinstanz für diese Anforderungen. Manuelle Reviews ersetzen ihn nicht.

Aktueller Test-Status: **PARTIAL FAIL** — 3 testid-Gaps (drift-run-summary, drift-severity-breakdown, drift-type-breakdown) führen zu FAIL bis DriftDashboard.jsx migriert ist.
