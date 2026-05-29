# M5 Data Aging & Entropy Audit

Ziel dieses Audits ist die fruehe Erkennung langsamer Degeneration in langlaufenden M5-Systemen. Der Audit nutzt die aktuelle Longrun-Simulation und Retrieval-Baseline als Evidenzquellen und trennt harte Messwerte von offenen Residualrisiken.

## Ausfuehrung

```bash
cd backend
python -m app.cli m5 entropy-audit
```

Der Lauf erzeugt:

- `historische M5-Entropy-Archivkopie`
- `reports/current/masterplan_status.json`
- `reports/current/masterplan_status.json`

## Entropie-Kategorien

| Kategorie | Wachstum ueber Zeit | Erkennungsstrategie | Cleanup-/Repair-Strategie |
|---|---|---|---|
| stale Queue Jobs | Queue-Backlog und Status-Age ueber Simulationszyklen | Status-Buckets nach `pending`, `running`, `retryable`, `dead_letter`; Age-Checks fuer `claimed_at`/`updated_at` | Timeout von `running` nach `retryable`, Dead-Letter-Replay mit Advisory Lock, Audit-Spur erzwingen |
| veraltete Backups | Maximalalter seit letzter erfolgreicher Restore-Verifikation | Letzten erfolgreichen Backup-/Verify-/Restore-Dry-Run-Zeitpunkt messen | Readiness failen, wenn kein frisches verifiziertes Backup existiert; alte Backups erst nach neuer Restore-Verifikation rotieren |
| orphan growth | Orphans pro Zyklus | Chunks ohne Version, Dateien ohne Dokument, Indexeintraege ohne DB-Chunk, Citations ohne Snapshot pruefen | Dry-run zuerst; nur eindeutig unerreichbare Daten entfernen; historische Citations schuetzen |
| stale Indexeintraege | Stale Index Growth nach Lifecycle- und Restore-Events | Index gegen DB-Lifecycle-State vergleichen | Workspace-scoped Reindex, archived/deleted Eintraege entfernen, Drift erneut pruefen |
| historische Citation Drift | Citation Completeness und Lifecycle-Exclusion-Violations | Golden Citation Queries wiederholen und Snapshotfelder pruefen | Citation-Snapshots nicht ueberschreiben; fehlenden `source_status` reparieren |
| duplicate growth | Duplicate Golden Query plus spaeter Live-DB-Aggregation | `workspace_id + content_hash` und normalisierte Metadaten aggregieren | `content_hash`-Eindeutigkeit erhalten; Merge nur auditiert und citations-schonend |
| Cleanup-Rueckstaende | Dry-run Candidate/Blocked Count ueber Zeit | Cleanup Dry-Runs versionieren und Delta auswerten | Wiederkehrende Kandidaten in Retention-Regeln ueberfuehren; `blocked_count` muss vor Loeschung 0 sein |

## Bewertung

- `low`: Aktuelle Baseline zeigt kein Wachstum oder liegt klar unter Schwelle.
- `medium`: Kontrolliert, aber noch nicht vollstaendig live gemessen oder nahe an Warnschwelle.
- `high`: Stop-Kriterium verletzt oder harte Drift erkennbar.

Aktueller Audit-Status wird aus den Kategorien abgeleitet:

- `pass`: keine mittleren oder hohen Aging-Risiken.
- `watch`: mindestens ein mittleres Risiko, aber kein harter Blocker.
- `blocked`: mindestens ein hohes Risiko.

## Praevention

- Entropy Audit nach jedem Longrun-Lauf und vor M5-Freigaben ausfuehren.
- M5-Gate auf `stale_index_growth=0`, `orphan_growth=0`, `lifecycle_exclusion_violations=0` und erfolgreiche Restore-Verifikation haerten.
- Report-Deltas ueber Zeit speichern, damit langsame Degeneration vor Schwellwertverletzung sichtbar wird.
- Fuer `duplicate growth` zusaetzlich eine Live-DB-Cardinality-Pruefung nachziehen; Golden Queries allein beweisen nur die Retrieval-/Policy-Seite.

