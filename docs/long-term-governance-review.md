# Long-Term Governance Review

Stand: 2026-05-13

## Ziel

Bewertet den aktuellen Kontrolgrad der acht Governance-Bereiche. Maßstab ist nicht Dokumentationsumfang, sondern operative Kontrollwirkung: Werden Abweichungen erkannt, sind Gates aktiv, sind Repair-Pfade ausführbar?

Bewertungsstufen:

- **fragmentiert**: Regeln unvollständig oder verstreut; keine Gate-Wirkung
- **teilweise kontrolliert**: Kernregeln definiert; einzelne Gates aktiv; Lücken in Ausführung oder Messung
- **überwiegend kontrolliert**: Gates und Regeln vollständig; einzelne Nachweise oder Automatisierungslücken
- **systemisch kontrolliert**: vollständige Gate-Kaskade; maschinenlesbare Nachweise; Repair-Pfade ausführbar; kein blinder Fleck

---

## 1. Truth Governance

**Dokument**: `docs/operational-truth-governance.md`

**Bewertung**: **systemisch kontrolliert**

Begründung:
- 15 verbindliche Regeln mit klarer Hierarchie (Report > Markdown > Dokumentation)
- Gate-Policies für M4, M5, Restore, Cleanup und Observability vollständig
- Statusvokabular (`pass`, `fail`, `unknown`, `partial`, `watch`, `blocked`) konsistent durchgezogen
- SQLite-Verbot als finale Gate-Wahrheit explizit und begründet
- Mindestfelder für Gate-Artefakte maschinenlesbar definiert

Verbleibende Lücke: Historische Reports akkumulieren ohne Archivierungsregel. Kein automatischer Mechanismus, der veraltete Reports als `unknown` markiert.

---

## 2. Drift Governance

**Dokumente**: `docs/drift.md`, `docs/operational-drift-dashboard-scope.md`, `docs/m5-data-aging-entropy-audit.md`

**Bewertung**: **teilweise kontrolliert**

Begründung:
- Drift-Arten vollständig klassifiziert (DB vs. Index, Lifecycle, Citation, Queue, Backup, Retrieval-Qualität)
- Entropy-Metriken definiert und implementiert (`entropy_helpers.py`, `m5_metrics.py`)
- Schwellen (`STALE_RATE_MAX`, `ORPHAN_RATE_MAX`, `RETRIEVAL_COVERAGE_MIN`) definiert
- Entropy-Truth-Tests vorhanden (`test_entropy_truth.py`)

Lücken:
- Drift Detection ist in `docs/drift.md` explizit als **Vorbereitung, nicht gestartet** klassifiziert
- Kein laufender Drift-Service; keine automatische Erkennung im Betrieb
- Drift-Repair-Runbook (`docs/runbooks/m5-drift-repair-strategy.md`) vorhanden, aber Auslösung ist manuell
- Kein maschinenlesbarer Drift-Report aus laufendem System (`reports/m5_drift/latest.json` ausstehend)
- `m5_drift_score` ist metrisch definiert, aber ohne kontinuierliche Produzentenquelle

---

## 3. Recovery Governance

**Dokumente**: `docs/controlled-failure-philosophy.md`, `docs/runbooks/`, `docs/m4e-backup-restore.md`

**Bewertung**: **überwiegend kontrolliert**

Begründung:
- 5 Fehlerprinzipien vollständig mit Regeln und Verboten
- 7 Recovery-Kategorien mit Eintrittspunkten und Verifikationspflichten
- Crash-Recovery-Tests vorhanden (`test_m4_crash_recovery_truth.py`, `test_rc3_chaos_truth.py`)
- Advisory-Lock-Recovery explizit modelliert

Lücken:
- Runbooks (`docs/runbooks/`) sind vorhanden, aber nicht systematisch mit `controlled-failure-philosophy.md` verlinkt
- Kein Recovery-SLA (Abschnitt SLA-6 im `operational-sla-framework.md` definiert Restore-Zeit, aber Recovery-Zeit für Job-Failures ohne SLA)
- Chaos-Tests existieren (`test_rc3_chaos_truth.py`), aber kein Pflicht-Trigger für neue F3-Features außer Dokumentation

---

## 4. Cleanup Governance

**Dokumente**: `docs/cleanup.md`, `backend/app/services/cleanup_governance.py`

**Bewertung**: **teilweise kontrolliert**

Begründung:
- `CleanupGovernanceService` ist implementiert und hat postgres_truth-Tests (`test_cleanup_governance_truth.py`, `test_m5_cleanup_truth.py`)
- Dry-Run-Pflicht, Citation-Schutz und aktive-Daten-Schutz sind im Service erzwungen
- `blocked_count`-Gate und Audit-Events vorhanden

Lücken:
- `docs/cleanup.md` deklariert explizit: **Mutationspfad nicht freigegeben** — kein destructiver Cleanup im Betrieb aktiv
- Kein laufender Cleanup-Scheduler; alle Cleanup-Läufe sind manuell
- Retention-Regeln für Cleanup-Kandidaten (wie alt muss ein Orphan sein, bevor er Kandidat wird?) nicht in Governance-Dokument festgelegt
- Cleanup-Audit-Trail unvollständig: `actor`-Feld fehlt in `cleanup_governance.py` (dokumentiert in `audit-trail-schema.md`)
- Keine Cleanup-Frequenz-SLA: wie oft muss Dry-Run laufen, ab wann ist Nicht-Laufen eine SLA-Verletzung?

---

## 5. Feature Governance

**Dokument**: `docs/feature-governance-model.md`

**Bewertung**: **systemisch kontrolliert**

Begründung:
- 4 Risikoklassen F1–F4 mit vollständigen, differenzierten Pflichtnachweisen
- 7 Pflichtbewertungen (Truth, Recovery, Drift, Isolation, Cleanup, Backup/Restore, Retrieval) für jedes Feature
- Chaos-Test-Pflicht für F3/F4 explizit
- Neues-Gate-Pflicht für F4 explizit
- Feature-Control-Prozess in 5 Phasen vollständig

Verbleibende Lücke: Keine automatisierte Klassifizierungs-Checkliste im PR-Prozess; die Governance ist dokumentiert, aber nicht in CI oder PR-Templates verankert.

---

## 6. Schema Governance

**Dokument**: `docs/schema-evolution-safety-model.md`

**Bewertung**: **systemisch kontrolliert**

Begründung:
- 4 Risiko-Klassen A–D mit vollständigen Pflichtprüfungen und Codebeispielen
- 11 Schema-Evolution-Regeln (SE-01 bis SE-11) mit konkreten Verboten
- Downgrade-Bewertungsmatrix und Alembic-Head-Truth-Validierung vollständig
- Jede Migrations-Klasse hat einen definierten Restore-Test-Trigger
- Pflicht-Header-Format erzwingt Selbstklassifizierung

Verbleibende Lücke: Namens-Präfix-Konvention (SE-01) wird nicht automatisch durch CI-Lint geprüft. Compliance liegt bei manueller Review.

---

## 7. Retrieval Governance

**Dokument**: `docs/retrieval-stability-contract.md`

**Bewertung**: **systemisch kontrolliert**

Begründung:
- 7 Stabilitätsbereiche vollständig mit expliziten Stabilitätsregeln
- Breaking-Change-Definition mit Nicht-Breaking-Ausnahmen vollständig
- Versionierungsstrategie (`retrieval-contract-vN`, `m5-retrieval-golden-vN`) operativ definiert
- 11 Regressionssignale mit maschinenlesbaren Stop-Regeln
- Golden Query Benchmark mit Aktualisierungspflicht und Schutz bestehender Queries

Verbleibende Lücke: `m5-retrieval-golden-v1` ist als Dataset-Version benannt, aber kein explizites Verzeichnis mit dem aktuellen Golden-Query-Korpus ist versioniert auffindbar.

---

## 8. Audit Governance

**Dokument**: `docs/audit-trail-schema.md`

**Bewertung**: **überwiegend kontrolliert**

Begründung:
- 8 Eventtypen mit vollständigen JSON-Schemas und Pflichtfeldern
- Retention-Regeln mit Fristen und Invarianten vollständig
- Korrelations-Regeln und Gate-Mapping definiert
- Reindex- und Cleanup-Services haben Audit-Events bereits implementiert

Lücken:
- **`actor`-Feld fehlt in der Implementierung** (`reindex_governance.py`, `cleanup_governance.py`): `log_event()` hat kein `actor`-Argument — als offene Lücke in `audit-trail-schema.md` dokumentiert, aber noch nicht behoben
- Restore- und Lifecycle-Wechsel-Events sind noch nicht vollständig implementiert (Service-seitig)
- Kein zentrales Audit-Store: Events werden in strukturierte Logs geschrieben, aber ohne Query-fähigen Audit-Trail-Store (kein dediziertes `audit_events`-Table)
- Retention-Durchsetzung (wer löscht, wer archiviert) ist nicht implementiert

---

## 9. Gesamtbild

| Bereich | Bewertung | Gate aktiv? | Messung aktiv? |
|---|---|---|---|
| Truth Governance | systemisch kontrolliert | ja | ja |
| Feature Governance | systemisch kontrolliert | ja | dokumentiert |
| Schema Governance | systemisch kontrolliert | ja | ja |
| Retrieval Governance | systemisch kontrolliert | ja | teilweise |
| Recovery Governance | überwiegend kontrolliert | teilweise | teilweise |
| Audit Governance | überwiegend kontrolliert | teilweise | teilweise |
| Drift Governance | teilweise kontrolliert | nein (vorbereitet) | kein laufender Service |
| Cleanup Governance | teilweise kontrolliert | nein (nur Dry-Run) | manuell |

---

## 10. Verbleibende Kontrolllücken

### Lücke L-01: Drift Detection ohne laufenden Service (Drift Governance)

**Risiko**: Drift akkumuliert unbemerkt. Stale-Index-Einträge und Orphan-Chunks wachsen, bis ein manueller Entropy-Lauf sie aufdeckt. Zwischen Läufen existiert kein Frühwarnsystem.

**Schwere**: HIGH — Retrieval-Coverage-Degradation ist schleichend und ohne kontinuierliche Messung nicht sichtbar.

**Schließungspfad**: Drift-Service als Background-Scheduler implementieren; `reports/m5_drift/latest.json` als kontinuierliche Truth-Quelle etablieren.

---

### Lücke L-02: Cleanup-Mutationspfad nicht freigegeben (Cleanup Governance)

**Risiko**: Orphan-Daten akkumulieren dauerhaft. Ohne freigegebenen Mutationspfad kann kein kontrollierter Cleanup stattfinden. Ad-hoc-Eingriffe ohne Governance-Struktur werden wahrscheinlicher.

**Schwere**: HIGH — steigendes Orphan-Volumen belastet Entropy-Score und Retrieval-Coverage.

**Schließungspfad**: Destructive-Cleanup-Gate formell freigeben (nach positivem Dry-Run-Gate + Backup); Cleanup-SLA (Frequenz) definieren.

---

### Lücke L-03: `actor`-Feld fehlt in Audit-Trail-Implementierung (Audit Governance)

**Risiko**: Auditpflichtige Operationen (Reindex, Cleanup) können nachträglich nicht einer auslösenden Entität zugeordnet werden. Compliance-Anforderungen und Incident-Analyse sind eingeschränkt.

**Schwere**: MEDIUM — Gates funktionieren, aber Accountability-Trail ist unvollständig.

**Schließungspfad**: `log_event()` um `actor`-Parameter erweitern; alle `run_governed_*()`-Methoden übergeben `actor` aus Auth-Kontext.

---

### Lücke L-04: Golden-Query-Korpus nicht versioniert auffindbar (Retrieval Governance)

**Risiko**: Retrieval-Stabilität ist dokumentarisch definiert, aber der Referenz-Datensatz (`m5-retrieval-golden-v1`) ist nicht als versioniertes Artefakt auffindbar. Regressionsschutz hängt an einem benannten, aber nicht lokalisierbaren Korpus.

**Schwere**: MEDIUM — Regression Detection läuft, aber Baseline-Vergleich ohne zugänglichen Korpus ist nicht reproduzierbar.

**Schließungspfad**: Golden-Query-Korpus als Datei unter `tests/retrieval_benchmark/golden/v1/` versionieren; `retrieval-stability-contract.md` auf konkreten Pfad zeigen.

---

### Lücke L-05: PostgreSQL-Truth-Tests noch skippable (Truth Governance)

**Risiko**: Ohne `TEST_DATABASE_URL` laufen Truth-Tests nicht. CI-Umgebungen ohne dedizierte PostgreSQL-Instanz liefern false-positive Gate-Ergebnisse (TD-P5-001, Score 675).

**Schwere**: HIGH — betrifft alle Gate-Entscheidungen gleichzeitig.

**Schließungspfad**: `TEST_DATABASE_URL` in CI-Pipeline bereitstellen; Gate-Validator `validate_m4_truth_gate.py` verwirft Skip-Ergebnisse für Pflichtgates.

---

### Lücke L-06: Kein zentraler Audit-Store (Audit Governance)

**Risiko**: Audit-Events landen in strukturierten Logs, aber ohne Query-fähigen Store. Langzeitaudit-Anfragen (alle Reindexes in den letzten 90 Tagen) erfordern Log-Mining statt DB-Abfrage.

**Schwere**: MEDIUM — operativer Betrieb funktioniert, aber Audit-Qualität für Compliance und Incident-Analyse ist begrenzt.

**Schließungspfad**: `audit_events`-Tabelle mit Retention-Logik einführen (Klasse-B-Migration); als F3-Feature klassifizieren.

---

## 11. Höchste Langzeitrisiken

### Risiko R-01: Schleichende Drift ohne Frühwarnung

Ohne laufenden Drift-Service ist Retrieval-Coverage-Degradation unsichtbar bis zu einem manuellen Lauf. In einem Mehrbenutzersystem mit kontinuierlichem Import kann Coverage monatelang sinken, bevor ein Operator es bemerkt.

**Zeitrahmen**: ab ca. 3–6 Monate aktivem Betrieb kritisch.

**Mitigation**: Drift-Service als erste Priorität in nächstem Milestone; `RETRIEVAL_COVERAGE_MIN`-Verletzung als automatischer Alert.

---

### Risiko R-02: Orphan-Akkumulation ohne Cleanup-Freigabe

Jeder Import, jede Migration, jede Reindex-Operation kann Orphan-Daten erzeugen. Ohne freigegebenen Cleanup-Pfad wachsen Orphan-Raten monoton. Nach 12+ Monaten kann Orphan-Volumen Entropy-Score dauerhaft über Schwelle treiben.

**Zeitrahmen**: ab ca. 6–12 Monate aktivem Betrieb relevant.

**Mitigation**: Cleanup-Dry-Run als Bestandteil des regulären Betriebszyklus (SLA definieren); Mutationspfad-Freigabe nach positivem Dry-Run-Gate.

---

### Risiko R-03: Audit-Accountability-Lücke bei Incidents

Ohne `actor`-Feld in Audit-Events und ohne zentralen Audit-Store ist bei einem Incident (z.B. unerwarteter Reindex mit Drift-Delta) nicht direkt rekonstruierbar, wer die Operation ausgelöst hat. Incident-Analyse dauert länger; Compliance-Nachweise sind schwächer.

**Zeitrahmen**: ab erstem Produktionsvorfall relevant.

**Mitigation**: `actor`-Feld als nächste Implementierungsaufgabe (Low-Aufwand, hohe Accountability-Wirkung).

---

### Risiko R-04: False-Positive Gate-Ergebnisse ohne PostgreSQL in CI

TD-P5-001 (Score 675): Solange `TEST_DATABASE_URL` optional ist, können SQLite-Läufe als Gates fungieren. Schemaänderungen, die PostgreSQL-spezifisches Verhalten brechen, werden nicht erkannt. Produktionsverhalten und Test-Verhalten divergieren still.

**Zeitrahmen**: jede Migration ist potenziell betroffen.

**Mitigation**: `TEST_DATABASE_URL`-Pflicht im CI vor nächstem Milestone-Gate.
