# M5 Cleanup

Stand: 2026-05-29

## Status

- Phase: Vorbereitung abgeschlossen
- Implementierung: nicht gestartet
- Freigabestatus: Dry-Run-Konzept freigegeben; produktiver Mutationspfad explizit deferred
- Cleanup gilt in M5 ausschließlich als Dry-Run-Planungs- und Bewertungsbereich

---

## Scope

| Kandidat-Typ | Erkennungslogik |
|---|---|
| Orphaned Chunks | `document_version_id` referenziert keine existierende Version |
| Orphaned Versions | `document_id` referenziert kein existierendes Dokument |
| Stale Index Entries | Index-Eintrag ohne korrespondierenden DB-Chunk |
| Alte Dead-Letter Jobs | `status = dead_letter` und älter als Retention-Schwelle |
| Temporäre Upload-Dateien | Upload-Artefakte ohne abgeschlossenen Job |
| Abgelaufene Sessions | `auth_sessions` jenseits Ablaufzeitstempel |
| Alte Reports | Reports älter als Retention-Fenster |

---

## Safety Constraints (verbindlich)

1. Dry Run zuerst — kein Löschlauf ohne vorherigen Dry-Run
2. Keine Löschung ohne Report
3. Keine Chat-Citation zerstören — Citations mit `source_status = active` sind geschützt
4. Stop bei `blocked_count > 0`
5. Backup vor Mutation — produktiver Löschlauf nur nach verifizierbarem Backup
6. Audit-Spur — jede mutierende Aktion erzeugt einen Audit-Log-Eintrag

---

## Schutzklassen

| Schutzklasse | Entitäten | Begründung |
|---|---|---|
| `citation_referenced` | Chunks mit aktiver oder historischer Citation | Retrieval-Stabilität |
| `active_document` | Versions und Chunks aktiver Dokumente | Lifecycle-Integrität |
| `pending_job` | Temporäre Dateien mit pending/running Job | Upload-Integrität |
| `recent_backup` | Reports und Manifeste jünger als Retention | Restore-Fähigkeit |

---

## Dry-Run Output

```json
{
  "report_type": "cleanup_dry_run",
  "generated_at": "<iso8601>",
  "workspace_id": "<uuid>",
  "status": "ready | blocked",
  "candidate_count": 0,
  "protected_count": 0,
  "blocked_count": 0,
  "candidates": [{ "type": "orphaned_chunk", "count": 0, "sample_ids": [] }],
  "blocked_reasons": []
}
```

`status = blocked` wenn `blocked_count > 0`. Kein Löschlauf bei `status = blocked`.

---

## Retention-Regeln (konfigurierbar)

| Kandidat-Typ | Standard |
|---|---|
| Dead-Letter Jobs | 30 Tage nach `updated_at` |
| Abgelaufene Sessions | 7 Tage nach `expires_at` |
| Temporäre Upload-Dateien | 24 Stunden nach Job-Abschluss |
| Alte Reports | 90 Tage |

---

## Nicht-Scope

- Keine produktive Löschung ohne explizite Freigabe
- Kein automatischer Cleanup
- Keine stille Mutation von References, Citations oder Originaldateien

---

## Implementierungsanker

- CLI (Dry-Run): `python -m app.cli m5 cleanup-dry-run --workspace <id>`
- Report-Ziel: `reports/current/m5_cleanup_dry_run_report.json`
- Truth-Test-Block: `cleanup_dry_run`
