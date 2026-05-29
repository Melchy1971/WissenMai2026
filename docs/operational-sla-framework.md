# Operational SLA Framework

Stand: 2026-05-13

## Ziel

Betriebliche Schwellen sind verbindlich. Jede SLA-Verletzung ist ein messbares Ereignis, das eine definierte Eskalation auslÃ¶st. Schwellen werden aus maschinenlesbaren Reports abgeleitet, nicht aus manuellen Status-EinschÃ¤tzungen.

Verwandte Dokumente:

- `docs/m5-observability.md` â€” maschinenlesbare Metrikdefinitionen
- `docs/operational-truth-governance.md` â€” Truth-Quellen und Gate-Policies
- `docs/runbooks/m5-operations-model.md` â€” Betriebsmodell
- `docs/runbooks/m5-drift-repair-strategy.md` â€” Repair-Eskalation

---

## 1. SLA-Matrix

FÃ¼r jede SLA gilt:

- **Zielwert**: normaler Betrieb; kein Handlungsbedarf
- **Warnschwelle**: erhÃ¶htes Risiko; Monitoring intensivieren, Ursache identifizieren
- **Kritische Schwelle**: SLA-Verletzung; sofortige Eskalation erforderlich
- **Messmethode**: welche Metrik oder welcher Report die Schwelle belegt
- **Eskalation**: was bei Warnung bzw. kritischem Zustand geschieht

---

### SLA-1: Upload-Verarbeitung

Verarbeitungszeit vom Job-Eingang (`created_at`) bis zum abgeschlossenen Import-Status (`completed`).

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | p95 < 30 s | normaler Import eines Dokuments mit Chunking und Indexierung |
| Warnschwelle | p95 > 120 s | Import deutlich verlangsamt; Ressourcen- oder Lock-Druck prÃ¼fen |
| Kritische Schwelle | p95 > 300 s oder `running`-Job ohne Fortschritt > Timeout | Import blockiert; aktive Running-Jobs prÃ¼fen auf Zombie-Zustand |

Messmethode: `m5_queue_backlog_age_seconds` (Job-Typ `document_import`, Status `running`); Queue-Aging-Report Feld `oldest_running_age_seconds`.

Eskalation Warnung: Queue-Aging-Report auswerten; Advisory-Lock-Konflikte prÃ¼fen; bei Anzeichen fÃ¼r stuck-Jobs Recovery-Runbook einleiten.

Eskalation Kritisch: sofortige Recovery-PrÃ¼fung; stuck Jobs identifizieren; Rollback oder Replay einleiten; `docs/runbooks/` konsultieren.

---

### SLA-2: Queue Delay

Wartezeit fÃ¼r `pending`- und `retryable`-Jobs bis zur ersten Verarbeitung (p95 Ã¼ber alle aktiven Workspaces).

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | p95 < 60 s | Jobs werden zeitnah aufgenommen |
| Warnschwelle | p95 > 300 s | Backlog baut sich auf; KapazitÃ¤t oder Starvation prÃ¼fen |
| Kritische Schwelle | p95 > 900 s oder Dead-Letter-Wachstum > 0 ohne Audit-Kontext | Queue-Starvation oder systematische Fehler |

Messmethode: `m5_queue_age_p95_seconds`; `m5_dead_letter_growth` (24h-Fenster); Queue-Aging-Report Feld `queue_age_p95_seconds`.

Eskalation Warnung: Workspace-Verteilung aus `m5_workspace_queue_distribution` prÃ¼fen; Starvation-Signale identifizieren.

Eskalation Kritisch: Dead-Letter-Replay prÃ¼fen; Worker-KapazitÃ¤t skalieren; bei Starvation eines Workspaces PrioritÃ¤ts-Reset einleiten.

---

### SLA-3: Search-Antwortzeit

Latenz von `GET /api/v1/search/chunks` (p95, gemessen end-to-end am API-Gateway oder im strukturierten Log).

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | p95 < 500 ms | FTS-Abfrage mit Lifecycle-Filterung, Workspace-Isolation und Ranking |
| Warnschwelle | p95 > 1 000 ms | Abfrage-Performance degradiert; Index-Gesundheit und DB-Load prÃ¼fen |
| Kritische Schwelle | p95 > 2 000 ms oder Fehlerrate > 1 % | Search nicht betriebsbereit |

Messmethode: strukturiertes JSON-Log-Event `search_request_completed` mit Feldern `duration_ms`, `workspace_id`, `status`; kein Querytext im Log.

Eskalation Warnung: `EXPLAIN ANALYZE` auf langsame Queries; GIN-Index-Gesundheit prÃ¼fen; `is_searchable`-Rate und Orphan-Rate aus Drift-Report prÃ¼fen.

Eskalation Kritisch: Search-Circuit-Breaker oder degradierten Modus erwÃ¤gen; DB-Verbindungspool und Lock-Zustand prÃ¼fen.

---

### SLA-4: Chat-Retrieval-Antwortzeit

Latenz des RAG-Retrieval-Pfads von Chat-Request bis erster Token-Ausgabe (p95). Umfasst Search, Context Builder, Citation Mapper â€” nicht die LLM-Generierungszeit.

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | p95 < 2 000 ms | Retrieval-Pfad mit Search, Kontext-Assembly und Citation-Mapping |
| Warnschwelle | p95 > 4 000 ms | Retrieval deutlich verlangsamt; Context-Builder oder Citation-Pfad unter Druck |
| Kritische Schwelle | p95 > 8 000 ms oder Citation-Fehlerrate > 1 % | RAG-Pfad nicht zuverlÃ¤ssig nutzbar |

Messmethode: strukturiertes Log-Event `chat_retrieval_completed` mit Feldern `retrieval_duration_ms`, `citation_count`, `context_size_tokens`, `workspace_id`; kein Chunk- oder Querytext.

Eskalation Warnung: Citation-Completeness aus `reports/current/masterplan_status.json` prÃ¼fen; Context-Builder-Timeout-Konfiguration prÃ¼fen.

Eskalation Kritisch: insufficient-context-Rate auswerten; Search-Antwortzeit (SLA-3) als Ursache ausschlieÃŸen; bei systematischem Retrieval-Ausfall RAG-Fallback aktivieren.

---

### SLA-5: Backup-Freshness

Alter des zuletzt erfolgreich verifizierten Backups (Zeit seit `verified_at` im Backup-Manifest).

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | â‰¤ 24 h | tÃ¤gliches Backup mit Verify-Lauf |
| Warnschwelle | > 6 Tage | Backup Ã¤lter als Toleranzfenster; nÃ¤chster Backup-Lauf forcieren |
| Kritische Schwelle | > 7 Tage oder letzter `verify_backup()` fehlgeschlagen | DR-FÃ¤higkeit nicht garantierbar |

Messmethode: `m5_backup_freshness_seconds`; Backup-Manifest `verified_at`; `BackupRestoreService.verify_backup()` RÃ¼ckgabe; `reports/current/m4e_backup_restore_truth.json`.

Eskalation Warnung: Backup-Job manuell anstoÃŸen; Verify-Lauf erzwingen; Backup-Ziel-VerfÃ¼gbarkeit prÃ¼fen.

Eskalation Kritisch: Disaster-Recovery-Runbook `docs/runbooks/disaster-recovery.md` einleiten; kein destruktiver Betrieb (Schema-Migrationen, Cleanup-Mutationen) bis Backup bestÃ¤tigt.

---

### SLA-6: Restore-Zeit

Zeit von Restore-Start bis zur vollstÃ¤ndig verifizierten Zieldatenbank (inkl. `alembic upgrade head`, postgres_truth-Smoke, Reindex-Smoke). Gilt fÃ¼r einen typischen Produktionsdatensatz.

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | < 30 min | schnelle Wiederherstellung bei kleinem bis mittlerem Datensatz |
| Warnschwelle | > 60 min | Restore-Prozess verlangsamt; DatengrÃ¶ÃŸe oder Reindex-Performance prÃ¼fen |
| Kritische Schwelle | > 120 min oder Verify-Fehler nach Restore | RTO nicht haltbar; Restore-Prozess hat strukturelles Problem |

Messmethode: Restore-Truth-Report Feld `restore_duration_seconds`; `BackupRestoreService.verify_backup()` Ergebnis; postgres_truth-Smoke nach Restore.

Eskalation Warnung: Restore-Lauf isoliert wiederholen; Reindex-Performance nach Restore gesondert messen; Manifest-VollstÃ¤ndigkeit prÃ¼fen.

Eskalation Kritisch: Datenverlust-Risiko bewerten; alternative Backup-Generation prÃ¼fen; Incident-Pfad aus Disaster-Recovery-Runbook einleiten.

---

### SLA-7: Drift-Detection-AktualitÃ¤t

Alter des letzten vollstÃ¤ndigen Drift-Reports (Zeit seit `generated_at` im aktuellen Drift-/Entropy-Report).

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | < 24 h | tÃ¤glicher Entropy- und Drift-Report |
| Warnschwelle | > 48 h | Drift-Zustand unbekannt; Drift-Lauf manuell anstoÃŸen |
| Kritische Schwelle | > 72 h oder `m5_drift_score > 0` persistierend nach Repair | Drift unkontrolliert; Repair-Eskalation erforderlich |

Messmethode: `m5_drift_score`; Entropy-Report `generated_at` aus `reports/current/masterplan_status.json`; Drift-Report `generated_at`.

Eskalation Warnung: Entropy-Audit manuell ausfÃ¼hren (`scripts/run_retrieval_benchmark.py` oder CLI-Ã„quivalent); STALE_RATE und ORPHAN_RATE aus Report auswerten.

Eskalation Kritisch: Drift-Repair-Strategie `docs/runbooks/m5-drift-repair-strategy.md` einleiten; bei persistentem Drift Ã¼ber 72 h kein Merge governance-pflichtiger Ã„nderungen.

---

### SLA-8: Cleanup-Laufzeiten

AusfÃ¼hrungszeit eines vollstÃ¤ndigen Cleanup-Dry-Run-Zyklus (inkl. Kandidaten-Sammlung, Schutzregeln, Dry-Run-Report).

| Stufe | Schwelle | Beschreibung |
|---|---|---|
| Zielwert | < 10 min | Dry-Run-Zyklus fÃ¼r einen Workspace |
| Warnschwelle | > 30 min oder `blocked_count > 0` | Cleanup-Logik unter Datendruck; Schutzregeln greifen unerwartet |
| Kritische Schwelle | > 60 min oder destructiver Plan ohne aktuelles Backup | Cleanup nicht betriebssicher; Mutation blockieren |

Messmethode: `m5_cleanup_impact` (Felder `candidate_count`, `protected_count`, `blocked_count`); Cleanup-Governance-Report `duration_seconds`.

Eskalation Warnung: Schutzregel-Hits analysieren (Citations, aktive Queue-Referenzen, aktive Dokumente); Candidate-Wachstum mit Orphan-Rate korrelieren.

Eskalation Kritisch: keine destructiven Cleanup-Mutationen ohne frisches Backup und `blocked_count = 0`; Cleanup-Governance-Service auf Fehler prÃ¼fen.

---

## 2. Betriebsmetriken â€” Kurzreferenz

| Metrik | SLA | Quelle | Workspace-Scope |
|---|---|---|---|
| `m5_queue_backlog_age_seconds` | SLA-1, SLA-2 | `background_jobs`, Queue-Aging-Report | ja |
| `m5_queue_age_p95_seconds` | SLA-2 | Queue-Aging-Report | ja |
| `m5_dead_letter_growth` | SLA-2 | Queue-Aging-Report | ja |
| `m5_workspace_queue_distribution` | SLA-2 | Queue-Aging-Report | ja |
| `m5_retry_frequency` | SLA-2 | `background_jobs.attempts` | ja |
| `m5_retrieval_quality_trend` | SLA-3, SLA-4 | `reports/current/masterplan_status.json` | global |
| `m5_backup_freshness_seconds` | SLA-5 | Backup-Manifest, Verify-Report | global |
| `m5_restore_success_rate` | SLA-6 | Restore-Truth-Report | global |
| `m5_drift_score` | SLA-7 | Drift-/Entropy-Report | ja |
| `m5_orphan_growth_rate` | SLA-7 | Entropy-/Data-Quality-Report | ja |
| `m5_cleanup_impact` | SLA-8 | Cleanup-Governance-Report | ja |

Maschinenlesbare Metrikdefinitionen: `backend/app/observability/m5_metrics.py`.

---

## 3. Eskalationsregeln

### 3.1 Eskalationsstufen

| Stufe | Name | Trigger | Reaktion |
|---|---|---|---|
| 0 | OK | alle SLAs im Zielbereich | kein Handlungsbedarf |
| 1 | Watch | mindestens eine SLA im Warnbereich | Monitoring intensivieren; Ursache identifizieren |
| 2 | Alert | mindestens eine SLA im kritischen Bereich | sofortige Analyse; Runbook einleiten |
| 3 | Incident | mehrere SLAs kritisch oder Datenverlust-Risiko | Eskalation an Betriebsverantwortlichen; destruktive Aktionen stoppen |

### 3.2 Automatische Blocksignale

Die folgenden Bedingungen blockieren automatisch Merge, Cleanup-Mutation oder Deployment:

| Bedingung | Blockiert |
|---|---|
| `m5_dead_letter_growth > 0` ohne Audit-Kontext | Merge governance-pflichtiger Ã„nderungen |
| `m5_backup_freshness_seconds > 7 Tage` | destructive Schemamigrationen (Klasse C/D), destructiver Cleanup |
| `m5_drift_score > 0` persistierend nach Repair > 72 h | Merge governance-pflichtiger Ã„nderungen |
| Restore-Verify fehlgeschlagen | alle Klasse-D-Migrationen, DR-Gate |
| `m5_cleanup_impact.blocked_count > 0` | destructive Cleanup-Mutation |
| Lifecycle-Exclusion-Violations > 0 | RAG-/Search-Gate, Merge Retrieval-Ã„nderungen |
| Citation-Completeness unter Schwelle | RAG-Freigabe, Chat-Release-Gate |

### 3.3 Eskalations-Kaskade

```
SLA-Verletzung erkannt
  â†’ Report auslesen (maschinenlesbar)
  â†’ Stufe bestimmen (Warn / Kritisch)
  â†’ Runbook Ã¶ffnen (docs/runbooks/)
  â†’ Blocksignal prÃ¼fen (Abschnitt 3.2)
  â†’ falls Blocksignal aktiv: Merge/Mutation stoppen
  â†’ Ursache beheben
  â†’ SLA-Metrik erneut messen
  â†’ Report aktualisieren
  â†’ Gate-Status neu bewerten
```

### 3.4 SLA-Status-Vokabular

Entspricht dem Statusvokabular aus `docs/operational-truth-governance.md`:

| Status | Bedeutung fÃ¼r SLA |
|---|---|
| `pass` | alle Schwellen im Zielbereich, maschinenlesbar belegt |
| `watch` | mindestens eine SLA im Warnbereich |
| `fail` | mindestens eine SLA im kritischen Bereich |
| `unknown` | kein aktuelles Artefakt fÃ¼r Messung vorhanden |
| `blocked` | Blocksignal aktiv; destructive Aktionen gestoppt |

Ein SLA-Bereich darf nur als `pass` dokumentiert werden, wenn ein aktueller maschinenlesbarer Report die Schwelle belegt. Dokumentation allein erzeugt keinen SLA-Status.

---

## 4. Messmethoden-Anforderungen

Jede SLA-Messung muss ein Artefakt erzeugen, das mindestens enthÃ¤lt:

- `generated_at`
- `sla_area`
- `metric_name`
- `measured_value`
- `unit`
- `target`
- `warn_threshold`
- `critical_threshold`
- `status` (`ok` / `warn` / `critical` / `unknown`)
- `source` (welcher Report oder welches Log-Event)
- `scope` (`workspace_id` oder `global`)

Fehlt ein aktuelles Artefakt fÃ¼r eine SLA, gilt der Status als `unknown`, nicht als `pass`.

---

## 5. Kurzcheckliste Betrieb

```
[ ] SLA-1 Upload-Verarbeitung: p95 < 30 s (Queue-Aging-Report)
[ ] SLA-2 Queue Delay: p95 < 60 s, dead_letter_growth = 0
[ ] SLA-3 Search-Antwortzeit: p95 < 500 ms (Log-Auswertung)
[ ] SLA-4 Chat-Retrieval: p95 < 2 000 ms (Log-Auswertung)
[ ] SLA-5 Backup-Freshness: â‰¤ 24 h (Manifest + Verify)
[ ] SLA-6 Restore-Zeit: < 30 min (Restore-Truth-Report)
[ ] SLA-7 Drift-AktualitÃ¤t: < 24 h, drift_score = 0
[ ] SLA-8 Cleanup-Laufzeit: < 10 min, blocked_count = 0
[ ] Kein aktives Blocksignal (Abschnitt 3.2)
[ ] Alle Reports aktuell und maschinenlesbar
[ ] Status nicht aus Dokumentation, sondern aus Reports abgeleitet
```


