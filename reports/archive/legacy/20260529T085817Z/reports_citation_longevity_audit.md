# Citation Longevity Audit

Stand: 2026-05-13

## Ergebnis

Status: `pass`

Nachweis:

```text
pytest backend/tests/postgres_truth/test_citation_longevity_truth.py -q
11 passed
```

Der Audit laeuft gegen echte PostgreSQL-Truth-Tests und simuliert Langzeitzyklen fuer historische Chat-Citations.

## Gepruefter Scope

| Kategorie | Nachweis |
|---|---|
| Alte `source_anchor` gueltig | `anchor_unverifiable_count`, `orphaned_anchor_count`, normalisierte Chunk-`source_anchor` Seeds |
| `quote_preview` stabil | `preview_stale_count` erkennt Abweichung zwischen Snapshot und aktuellem Chunk |
| Deleted Dokumente korrekt markiert | `deleted_not_marked_count` und Lifecycle-Delete-Sync |
| Restored Dokumente korrekt dargestellt | `restored_not_marked_count` und Archive-Restore-Sync |
| Rechunking zerstoert keine Referenzen unbemerkt | `rechunk_reference_risk_count`, Orphan- und Preview-Staleness-Simulation |
| Restore zerstoert keine Referenzen unbemerkt | `restore_reference_risk_count`, Status-Drift- und Anchor-Verifikation |

## Simulierte Langzeitzyklen

- `baseline_snapshot`
- `archive_status_sync`
- `delete_status_sync`
- `archive_restore_status_sync`
- `manual_status_drift_detection`
- `rechunk_orphan_detection`
- `quote_preview_staleness_detection`
- `workspace_isolation`

## Longevity Audit

| Befundklasse | Erwartung | Audit-Ergebnis |
|---|---|---|
| Clean State | Keine Citation-Drift, Severity `ok` | bestanden |
| Archive | historische Citation wird `archived`, keine Drift | bestanden |
| Delete | historische Citation wird `deleted`, keine aktive Anzeige geloeschter Quelle | bestanden |
| Restore | historische Citation wird wieder `active`, wenn Quelle verifizierbar ist | bestanden |
| Status Drift | manuell falscher `source_status` wird erkannt | bestanden |
| Deleted not marked | geloeschte Quelle mit aktiver Citation wird kritisch erkannt | bestanden |
| Rechunk Orphan | aktive Citation ohne `chunk_id` wird erkannt | bestanden |
| Preview Stale | veraenderter Chunk-Inhalt mit altem `quote_preview` wird erkannt | bestanden |
| Workspace Isolation | andere Workspaces beeinflussen den Audit nicht | bestanden |
| API Contract | Admin-Longevity-Endpoint liefert Audit-Scope, Risiken und Haertung | bestanden |

## Persistenzrisiken

Aktuell kontrollierte Risiken:

- `source_status` kann ohne Lifecycle-Sync von `documents.lifecycle_status` abweichen.
- Rechunking kann aktive Citations von `chunk_id` entkoppeln.
- `quote_preview` kann als historischer Snapshot vom aktuellen Chunk-Inhalt abweichen.
- Restore kann Citations nur dann korrekt reaktivieren, wenn Anchor und Quelle verifizierbar bleiben.
- Deleted-Dokumente duerfen in historischen Antworten sichtbar bleiben, aber nie als aktive Quelle erscheinen.

Aktueller Audit-Befund:

- Keine Persistenzrisiken im Clean-State-Szenario.
- Alle simulierten Degradationen werden erkannt.
- Kritische Degradation `deleted_not_marked` eskaliert auf `critical`.

## Notwendige Snapshot-Haertung

Pflicht-Haertungen fuer langfristige Stabilitaet:

1. Citation-Snapshots bleiben immutable: `source_anchor`, `quote_preview`, `document_title`, `source_status` duerfen nicht still ueberschrieben werden.
2. Zusaetzliche Snapshot-Felder fuer robustes Remapping vorbereiten: `content_hash`, `chunk_index`, `document_version_id`, optional `quote_hash`.
3. Rechunking darf aktive Citations ohne verifizierbaren neuen Anchor nicht als `active` belassen; Zielstatus ist `missing` mit Audit.
4. Repair von Citation-Drift braucht Report und Audit, keine stille Mutation.
5. Restore darf `source_status` nur dann auf `active` setzen, wenn Dokument und Anchor verifizierbar sind.
6. Cleanup darf historische Citation-Snapshots nicht loeschen oder zusammenfalten.

## Entscheidung

Citation Longevity ist fuer die aktuell simulierten Langzeitzyklen kontrolliert. Die naechste Haertungsstufe ist ein echtes persistiertes Anchor-Snapshot-/Hash-Feld, damit Rechunking und Restore auch nach vielen Versionen reparierbar bleiben.

