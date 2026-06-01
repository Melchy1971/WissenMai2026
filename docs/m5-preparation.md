# M5 Vorbereitung

Stand: 2026-05-29

## Statusgrundlage

- M3a RC: siehe `reports/current/m3a_release_candidate.json`
- M4 Backend RC: siehe `reports/current/m4_backend_release_candidate.json`
- M4e Operations Release: siehe `reports/current/m4e_operations_release_gate.json`
- M5a Start-Gate: siehe `reports/current/m5a_start_gate.json`
- Gesamtstatus: siehe `reports/current/masterplan_status.json`

M5a bleibt vorbereitet, wenn `reports/current/m5a_start_gate.json` keine `GO`-Entscheidung meldet. Implementierungsslices duerfen erst nach eigenem Slice-Start-Gate starten.

| Blocker | Beschreibung |
|---|---|
| KL-M5-002 | Truth-Abweichungen werden ueber Reports unter `reports/current/` bewertet; kein Slice darf produktiv gehen ohne passenden Truth-Block |
| KL-M5-003 | Operational Governance Gate erst nach M5-Start blockierend bewerten |
| KL-M5-004 | Pflicht-Artefakte fehlen: Retrieval-Baseline, Cleanup Dry-Run, Truth-Block je Slice |

Dieses Dokument ist das verbindliche Vorbereitungspaket. Es enthält keine Implementierungsaussagen und ersetzt keine freigegebenen Truth-Nachweise.

---

## 1. M5 Scope

M5 hat drei operative Verantwortungsbereiche:

### 1.1 Datenkonsistenz und Quality

- Invariantenprüfung für Dokumente, Versionen, Chunks und Citations
- Erkennung von orphaned Entities (Chunks ohne Version, Versions ohne Dokument, Citations ohne Chunk-Snapshot)
- Duplikatschutz-Audit auf `(workspace_id, content_hash)`
- Data Quality Report als maschinenlesbarer Output

### 1.2 Drift Detection und Repair-Steuerung

- DB vs. Search Index Divergenz messen
- Lifecycle-Status vs. Suchbarkeit prüfen
- Citation Snapshot vs. Live-Status vergleichen
- Queue State vs. Worker-Zustand überwachen
- Backup Manifest vs. aktuelle Datenlage prüfen
- Retrieval-Qualität über Zeit tracken
- Repair bleibt explizit ausgelöst und auditiert, kein Auto-Repair

### 1.3 Cleanup Dry-Run

- Orphaned Chunks, Versions, stale Index Entries, alte Dead-Letter Jobs, temporäre Upload-Dateien, abgelaufene Sessions als Kandidaten identifizieren
- Dry-Run erzeugt `candidate_count`, `protected_count`, `blocked_count`
- Kein produktiver Löschlauf ohne separates Freigabedokument

### 1.4 Health Score Berechnung

- Gewichteter Gesamtscore aus Data Quality, Drift, Queue Health, Search/Retrieval, Backup Freshness, Error Rate, Documentation Truth
- Statusklassen: `healthy`, `degraded`, `unhealthy`
- Kein betrieblicher Score ohne laufende Berechnungsgrundlage und freigegebenen Truth-Nachweis

### 1.5 Retrieval Quality Baseline

- Golden Dataset mit quantitativen Schwellen für Search und Chat Retrieval
- Regression Detection gegen gespeicherte Baseline
- Pflichtauslöser nach Reindex, Restore, Cleanup und Chunking-Änderungen

### 1.6 Observability

- Langfristige Betriebsmetriken: Queue Aging, Drift Score, Retrieval Quality Trend, Backup Freshness, Restore Success Rate, Cleanup Impact, Orphan Growth Rate
- Strukturierte JSON-Logs, keine sensitiven Inhalte
- Dashboard-Konzept: Workspace-Ansicht und Global-Ansicht

---

## 2. Nicht-Scope M5

Folgende Bereiche werden in M5 bewusst nicht implementiert:

| Bereich | Begründung |
|---|---|
| Produktiver Cleanup-Lauf | Nur Dry-Run; mutierende Loeschfreigabe erfordert separates Dokument und Audit |
| Auto-Repair bei Drift | Repair ist explizit ausgelöst, kein automatischer Reparaturpfad |
| OCR für gescannte PDFs | Explizit deferred, bleibt `OCR_REQUIRED` |
| Embeddings / Vektorsuche | Optional, nicht V1-kritisch |
| Analyse / Merge / Refine Fachlogik | Vorbereitet im Datenmodell, Fachlogik ist Post-M4 Feature |
| Mutierende Admin-Aktionen über Web-UI | M4d bleibt read-only; operative Aktionen über Runbooks und CLI |
| M4e Produktionshaertung Backup/Restore | Minimalpfad vorhanden; externe Betriebsvalidierung ist Post-M5 |
| API-Versioning Konsolidierung | `/api/v1/documents` Alias-Konsolidierung ist M4/M5 API hardening, kein M5-Gate-Kriterium |

---

## 3. Risiken

| ID | Bereich | Risiko | Schwere | Mitigationsstrategie |
|---|---|---|---|---|
| R-M5-01 | M5 Truth Failures | Aktuelle Truth-Abweichungen werden ueber Reports unter `reports/current/` bewertet | hoch | M5-Fehler isoliert reparieren; kein M5-Gate ohne erfolgreich bewertete M5-Truth-Suite |
| R-M5-02 | Cleanup | Dry-Run-Logik erkennt protected Entities nicht vollständig | mittel | `blocked_count > 0` als Stop-Kriterium; keine produktive Ausführung ohne manuellen Review |
| R-M5-03 | Drift Detection | Drift ohne Repair-Pfad fuehrt zu wachsender Divergenz zwischen DB und Index | mittel | Drift bleibt read-only bis ein Repair-Runbook per Report referenziert ist; Reindex ist workspace-scoped |
| R-M5-04 | Retrieval Regression | Chunking- oder Normalisierungsänderungen können Silent Regressions erzeugen | mittel | Pflichtauslöser für Retrieval-Benchmark nach jeder Chunking-Änderung |
| R-M5-05 | Health Score ohne Evidenz | Score-Berechnung ohne reale Messgrundlage gibt falsche Sicherheit | hoch | Score darf erst als betrieblich berichtet werden, wenn ein aktueller Report den PostgreSQL-Truth-Block `health_score` bewertet |
| R-M5-06 | Citation Drift | Archivierte oder gelöschte Chunks erscheinen in neuen Retrieval-Ergebnissen | hoch | Lifecycle-Exclusion-Violations = 0 als hartes Stop-Kriterium im Longrun-Benchmark |
| R-M5-07 | Backup/Restore | Restore nach Reindex ohne Qualitätsprüfung führt zu unerkannter Retrieval-Degradation | mittel | Retrieval-Benchmark ist Pflichtauslöser nach `--trigger restore` |
| R-M5-08 | Observability Lücken | Metriken ohne aktuelle Quelle erzeugen `unknown`-Status statt `ok` | niedrig | Dashboard-Statusableitung nur aus maschinenlesbaren, aktuellen Reports |

---

## 4. Data Quality Regeln

Vollständige Regelspezifikation: `docs/data-quality.md`

Zusammenfassung harter Fehler:

- Dokument ohne Version = Fehler
- Version ohne Chunks (außer `failed import`) = Fehler
- Chunk ohne `source_anchor` = Fehler
- Orphaned Chunk (kein gültiges `document_version_id`) = Fehler
- Orphaned Version (kein gültiges `document_id`) = Fehler
- Duplicate `content_hash` innerhalb Workspace = Fehler
- Dangling Citation mit `source_status = active` = Fehler

Truth-Test-Block: `data_quality`

---

## 5. Drift Detection Konzept

Vollständige Spezifikation: `docs/drift.md`

Drift-Arten:

- DB vs. Search Index
- Lifecycle vs. Suchbarkeit
- Citation Snapshot vs. Live-Status
- Queue State vs. Worker-Zustand
- Backup Manifest vs. aktuelle Daten
- Retrieval-Qualität über Zeit

Repair bleibt explizit ausgelöst. Strategie: `docs/runbooks/m5-drift-repair-strategy.md`

Truth-Test-Block: `drift_detection`

---

## 6. Cleanup Dry-Run Konzept

Vollständige Spezifikation: `docs/cleanup.md`

Kandidaten: orphaned Chunks, orphaned Versions, stale Index Entries, alte Dead-Letter Jobs, temporäre Upload-Dateien, abgelaufene Sessions, alte Reports.

Stop-Kriterium: `blocked_count > 0` blockiert jeden Cleanup-Lauf.

Truth-Test-Block: `cleanup_dry_run`

---

## 7. Health Score Konzept

Vollständige Spezifikation: `docs/health-score.md`

Gewichtung:

| Komponente | Gewicht |
|---|---:|
| Data Quality | 25 % |
| Drift | 20 % |
| Queue Health | 15 % |
| Search / Retrieval Health | 15 % |
| Backup Freshness | 10 % |
| Error Rate | 10 % |
| Documentation Truth | 5 % |

Statusklassen: `healthy` (Score ≥ 0.85), `degraded` (0.60–0.84), `unhealthy` (< 0.60)

Truth-Test-Block: `health_score`

---

## 8. Retrieval Quality Baseline Konzept

Vollständige Spezifikation: `docs/m5-retrieval-quality-baseline.md`

Golden Dataset: `m5-retrieval-golden-v1`

Schwellen (Auswahl):

| Metrik | Schwelle |
|---|---:|
| Search Precision@5 | ≥ 0.80 |
| Search Recall@5 | ≥ 0.85 |
| Chat Precision@5 | ≥ 0.75 |
| Citation Completeness | ≥ 0.90 |
| Lifecycle Exclusion Violations | 0 |

Baseline-Aktualisierung nur mit `--set-baseline` und dokumentierter Begründung.

Pflichtauslöser: Reindex, Restore, Cleanup, Chunking-Änderung.

---

## 9. Operations-Abhängigkeiten

| Abhängigkeit | Quelle | Status |
|---|---|---|
| PostgreSQL als produktive DB | `reports/current/m4_backend_release_candidate.json` | GO |
| Auth und Workspace-Isolation (M4a) | `reports/current/m4_backend_release_candidate.json` | GO |
| Upload-Queue mit persistierter Queue (M4b) | `reports/current/m4_backend_release_candidate.json` | GO |
| Dokument-Lifecycle (M4c) | `reports/current/m4_backend_release_candidate.json` | GO |
| Admin-Diagnostics read-only (M4d) | `docs/m4d-admin-diagnostics.md` | read-only, mutierende Aktionen deferred |
| Backup/Restore Minimalpfad (M4e) | `reports/current/m4e_backup_restore_truth.json` | Minimal GO; Produktionshaertung deferred |
| Alembic-Migrationen aktuell | Schema und Migrationen vorhanden | GO |
| Retrieval-Foundation M3b | `reports/current/masterplan_status.json` | GO |
| dev_bootstrap.ps1 | `docs/operations.md` | verfügbar |

---

## 10. Startbedingungen für M5 Implementierung

M5-Implementierung wird ueber `reports/current/m5a_start_gate.json` und slice-spezifische Gate-Reports bewertet. Vor Start jedes M5-Slices muessen folgende Bedingungen erfuellt sein:

| Bedingung | Nachweispfad | Pflicht |
|---|---|---|
| M4 Backend RC GO | `reports/current/m4_backend_release_candidate.json` | ja |
| M5 Startgate PASS in `masterplan_status.json` | `reports/current/masterplan_status.json` | ja |
| 15 M5-Truth-Failures aus aktueller Suite behoben | `reports/current/m4_truth_report.json` neu erzeugt | ja, vor M5-Truth-Gate |
| Retrieval-Baseline vorhanden | `python -m app.cli m5 retrieval-benchmark --set-baseline` ausgeführt | ja, vor erstem Benchmark-Lauf |
| Dry-Run vor produktivem Cleanup | Cleanup Dry-Run Report vorhanden, `blocked_count = 0` | ja, vor jedem Cleanup-Lauf |
| Drift Detection read-only | kein Auto-Repair ohne freigegebenes Runbook | ja |
| Health Score hat reale Messgrundlage | PostgreSQL-Truth-Block `health_score` durch aktuellen Report bewertet | ja, vor Score-Reporting |
| Kein sensitives Logging | Logging-Review gegen Verbotsliste in `docs/m5-observability.md` | ja |

Ein Slice gilt als implementierungsbereit, wenn sein Truth-Test-Block im aktuellen PostgreSQL-Truth-Report grün ist.
