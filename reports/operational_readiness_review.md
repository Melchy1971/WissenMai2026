# Operational Readiness Review

Stand: 2026-05-13

## Entscheidung

**Der aktuelle Betriebszustand ist nur eingeschraenkt betreibbar.**

Eine produktionsnahe Betriebsfreigabe ist aktuell nicht zulaessig.

Begruendung in Kurzform:

- Truth Governance, Retrieval Regression Detection, Queue Aging Detection, Reindex Governance und Operations Runbooks sind vorhanden.
- Backup/Restore ist im realen Minimal-Scope positiv nachgewiesen.
- Der aktuelle PostgreSQL-Truth-Report ist jedoch rot und blockiert damit jede starke Betriebsfreigabe.
- Drift Detection und Langzeit-/Entropy-Kontrolle sind teilweise vorbereitet und teilweise implementiert, aber nicht als vollstaendig gruener Gate-Pfad nachgewiesen.

## Bewertungsstufe

| Stufe | Bedeutung | Ergebnis |
|---|---|---|
| nicht betreibbar | kein belastbarer Betriebsrahmen, keine Kontrollmechanismen | nein |
| eingeschraenkt betreibbar | zentrale Kontrollen und Runbooks vorhanden, aber harte Gate- oder Integritaetsblocker offen | **ja** |
| kontrolliert betreibbar | Pflichtkontrollen vorhanden und aktuelle maschinenlesbare Nachweise fuer den relevanten Scope gruen | nein |
| produktionsnah betreibbar | End-to-End-Truth, Drift, Restore, Cleanup, Reindex, Queue und Langzeitmetriken grün und aktuell | nein |

## Readiness-Matrix

| Kriterium | Status | Nachweis | Bewertung |
|---|---|---|---|
| 1. Truth Governance vorhanden? | erfuellt | `docs/operational-truth-governance.md` | Das Regelwerk ist klar, aktuell und trennt Dokumentation von Wahrheit. |
| 2. Drift Detection vorhanden? | teilweise erfuellt | `docs/drift.md`, `docs/runbooks/m5-drift-repair-strategy.md` | Drift-Arten, Repair-Grenzen und Nachweisanker sind definiert, aber der Slice ist laut Status noch nicht freigegeben und noch nicht als gruener Detailreport etabliert. |
| 3. Retrieval Regression Detection vorhanden? | erfuellt | `docs/m5-retrieval-quality-baseline.md`, `reports/m5_retrieval_regression/latest.json` | Baseline, Trigger und aktueller Regressionsreport sind vorhanden; letzter Report steht auf `pass`. |
| 4. Backup/Restore validiert? | teilweise erfuellt | `docs/runbooks/backup-restore.md`, `reports/restore_truth_report.md`, `backend/tests/test_backup_restore_service.py` | Praktischer Restore-Truth im Minimal-Scope ist positiv, aber der harte Gate-Nachweis ist noch markdownbasiert und nicht voll maschinenlesbar. |
| 5. Cleanup Governance vorhanden? | teilweise erfuellt | `docs/runbooks/cleanup-governance.md`, `reports/postgres_truth/latest.json` | Governance-Regeln sind klar, aber Cleanup-Governance-Truth-Failures verhindern eine starke Freigabe. |
| 6. Queue Aging Detection vorhanden? | erfuellt | `backend/tests/postgres_truth/test_queue_aging_truth.py`, `reports/postgres_truth/latest.json` | Service und Truth-Abdeckung sind vorhanden; Queue-Aging-Truth ist im aktuellen Report gruen belegt. |
| 7. Reindex Governance vorhanden? | erfuellt | `docs/runbooks/reindex-governance.md`, `backend/tests/postgres_truth/test_reindex_governance_truth.py` | Governed Reindex mit Audit, Drift-Snapshot, Scope-Regeln und Regression-Pflicht ist implementiert und truth-geprueft. |
| 8. Langzeitmetriken vorhanden? | teilweise erfuellt | `reports/m5_longrun/latest.json`, `reports/m5_entropy/latest.json`, `docs/runbooks/m5-operations-model.md` | Longrun- und Entropy-Reports existieren, aber die zugehoerigen Truth-Bloecke sind noch nicht vollstaendig gruen. |
| 9. Operations Runbooks vorhanden? | erfuellt | `docs/operations.md`, `docs/runbooks/m5-operations-model.md`, `docs/runbooks/disaster-recovery.md` | Betriebsrhythmus, Eskalation, Backup, Drift, Queue, Reindex, Cleanup und DR sind dokumentiert. |

## Kritischste Risiken

| Risiko | Schwere | Nachweis | Wirkung auf Betriebsfreigabe |
|---|---|---|---|
| Voller PostgreSQL-Truth-Report ist rot | kritisch | `reports/postgres_truth/latest.json` | Blockiert jede Aussage oberhalb von `eingeschraenkt betreibbar`. |
| Citation Longevity und Entropy-Truth sind nicht gruen | hoch | `reports/postgres_truth/latest.json` | Schleichende Systemalterung ist noch nicht kontrolliert nachgewiesen. |
| Drift Detection ist nicht als gruener M5-Operativpfad geschlossen | hoch | `docs/drift.md` | Drift kann beschrieben werden, ist aber noch nicht als freigegebener Kontrollmechanismus abgesichert. |
| Cleanup Governance hat offene Truth-Failures | hoch | `reports/postgres_truth/latest.json` | Destructive Cleanup bleibt operativ gesperrt; selbst Governance ist noch nicht voll stabil. |
| Restore-Nachweis ist nicht voll maschinenlesbar | mittel | `reports/restore_truth_report.md`, `docs/operational-truth-governance.md` | Praktisch belastbar, aber fuer harte Gate-Automatisierung noch zu schwach. |
| Duplicate Growth ist nur teilweise gemessen | mittel | `reports/m5_entropy/latest.json` | Langzeitrisiko bleibt im Status `watch`, solange die Live-DB-Cardinality-Pruefung fehlt. |

## Aktuelle Evidenzlage

### Positive Evidenz

- Truth Governance ist aktuell dokumentiert und als Regelwerk belastbar.
- Retrieval Regression Detection ist implementiert und der letzte Reindex-Regression-Report ist `pass`.
- Queue Aging Detection ist implementiert und in PostgreSQL-Truth-Tests nachgewiesen.
- Reindex Governance ist implementiert und in PostgreSQL-Truth-Tests nachgewiesen.
- Restore auf leere Zielumgebung ist im geprueften Minimal-Scope real erfolgreich dokumentiert.
- Operations-, Cleanup-, Reindex- und DR-Runbooks sind vorhanden.

### Negative Evidenz

- `reports/postgres_truth/latest.json` meldet `failed = 29`, `pytest_exit_code = 1` und `M4-Gate BLOCKED`.
- Mehrere Failures liegen genau in betriebskritischen Bereichen: Citation Longevity, Cleanup Governance und Entropy.
- Der Drift-Slice ist laut Dokumentation weiterhin Vorbereitungsrahmen und nicht als freigegebener gruener Betriebsservice ausgewiesen.

## Betriebsfreigabe-Empfehlung

### Empfehlung

**Keine produktionsnahe Betriebsfreigabe.**

Zulaessig ist nur ein eingeschraenkter, kontrollierter Vorproduktionsbetrieb mit folgenden Grenzen:

- Diagnostics read-only
- Backup-Verifikation verpflichtend
- Reindex nur governed und mit nachgelagerter Regression-Pruefung
- Cleanup standardmaessig nur als Dry Run
- Drift-/Entropy-Befunde nur detect-only, keine stillen Auto-Repairs
- keine starke Release- oder Produktionsreifeaussage aus dem aktuellen Truth-Stand

### Freigabestatus

| Freigabeentscheidung | Ergebnis |
|---|---|
| nicht betreibbar | nein |
| eingeschraenkt betreibbar | **ja** |
| kontrolliert betreibbar | nein |
| produktionsnah betreibbar | nein |

## Bedingungen fuer Hochstufung auf kontrolliert betreibbar

1. `reports/postgres_truth/latest.json` muss auf `failed = 0`, `errors = 0`, `skipped = 0`, `pytest_exit_code = 0` kommen.
2. Die offenen Truth-Failures in Citation Longevity, Cleanup Governance und Entropy muessen geschlossen oder sauber aus dem Gate-Scope begruendet werden.
3. Drift Detection braucht einen aktuellen maschinenlesbaren Detailreport und einen eindeutig bewertbaren operativen Status.
4. Der Restore-Nachweis sollte zusaetzlich als JSON-/Validator-Artefakt vorliegen.
5. Duplicate Growth braucht die geplante Live-DB-Cardinality-Pruefung, damit Langzeitrisiken nicht nur als `watch` dokumentiert sind.

## Go/No-Go

**Go fuer eingeschraenkten Vorproduktionsbetrieb: ja.**

**Go fuer kontrollierten produktionsnahen Betrieb: nein.**

**Go fuer Betriebsfreigabe mit starkem Produktionsanspruch: nein.**
