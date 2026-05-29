# Dokumentation

Dokumentationsbereich fuer Architektur-, Entscheidungs- und Betriebswissen der Wissensbasis.

## Zweck

- Architektur und technische Leitplanken dokumentieren.
- ADRs nachvollziehbar versionieren.
- API-Notizen, Task-Kontrakte, Review-Prompts und Runbooks sammeln.
- Betriebswissen getrennt von Quellcode pflegen.

## Struktur

- `adr/`: Architekturentscheidungen.
- `api/`: Platz fuer API-Skizzen, Kontrakte und spaetere Endpunktdokumentation.
- `prompts/`: Hilfsdokumente fuer Reviews und Task-Vertraege.
- `runbooks/`: Betriebs- und Wiederherstellungsablaeufe.

Wichtige Runbooks im aktuellen Stand:

- [docs/runbooks/backup-restore.md](H:/WissenMai2026/docs/runbooks/backup-restore.md): operativer M4e-Minimalpfad fuer Backup und Restore
- [docs/runbooks/disaster-recovery.md](H:/WissenMai2026/docs/runbooks/disaster-recovery.md): szenariobasiertes DR-Runbook mit Operator-Guide und Checklisten
- [docs/runbooks/m5-operations-model.md](H:/WissenMai2026/docs/runbooks/m5-operations-model.md): M5-Betriebsmodell mit Checklisten und Eskalationsschwellen
- [docs/runbooks/m5-drift-repair-strategy.md](H:/WissenMai2026/docs/runbooks/m5-drift-repair-strategy.md): M5-Strategie fuer dry-run-first Drift Repair mit Auditpflicht

## Aktueller Freigabestand

Die kompakte Freigabefassung fuer den aktuell zulaessigen M4/M5-Dokumentationsstand steht in `docs/m4-m5-freigabefassung.md`.

Der aktuelle echte Restore-Truth-Nachweis steht in [reports/current/m4e_backup_restore_truth.json](H:/WissenMai2026/reports/current/m4e_backup_restore_truth.json).

Das Release-Candidate-Modell fuer Zwischenstatus zwischen Entwicklung und abgeschlossen steht in `docs/release-candidate-model.md`; die maschinenlesbare Quelle ist `docs/release-candidate-model.json`.

Der governance-stabile Entwicklungsmodus nach M3a/M4 steht in `docs/governance-stable-development-mode.md`; die maschinenlesbare Quelle ist `docs/governance-stable-development-mode.json`.

Sie ist die bevorzugte Kurzreferenz fuer:

- aktuellen M4-Hardening-Status
- read-only-Grenze von M4d
- Gate- und Freigabestand fuer M5
- Aussagen, die aktuell nicht als freigegeben dokumentiert werden duerfen

## M5 Vorbereitung

Die folgenden Dokumente bilden den Vorbereitungsrahmen fuer M5. Sie beschreiben aktuell nur Statuslogik, Konzepte und spaetere Nachweisanker.

Sie duerfen nicht als Beleg fuer einen gestarteten M5-Betrieb, eine laufende Implementierung oder ein gruÌˆnes M5-Gate gelesen werden.

- [docs/data-quality.md](H:/WissenMai2026/docs/data-quality.md): Vorbereitungsrahmen fuer M5 Data Quality
- [docs/drift.md](H:/WissenMai2026/docs/drift.md): Vorbereitungsrahmen fuer M5 Drift Detection
- [docs/cleanup.md](H:/WissenMai2026/docs/cleanup.md): Vorbereitungsrahmen fuer M5 Cleanup
- [docs/health-score.md](H:/WissenMai2026/docs/health-score.md): Vorbereitungsrahmen fuer M5 Health Score
- [docs/operations.md](H:/WissenMai2026/docs/operations.md): Betriebsrahmen inklusive M5-Dokumentationslogik
- [docs/operational-truth-governance.md](H:/WissenMai2026/docs/operational-truth-governance.md): Governance-Regeln fuer messbare Truth-Quellen und Gate-Policies
- [docs/governance-boundary.md](H:/WissenMai2026/docs/governance-boundary.md): Boundary-Regeln zwischen M3a, M4, M5 und Operational Governance
- [docs/governance-stable-development-mode.md](H:/WissenMai2026/docs/governance-stable-development-mode.md): Entwicklungsmodus gegen Rueckfall in feature-getriebene Arbeit nach M3a/M4
- [docs/feature-governance-model.md](H:/WissenMai2026/docs/feature-governance-model.md): kontrollierte Einfuehrung neuer Features mit Risikoklassen und Pflichtnachweisen
- [docs/m5-observability.md](H:/WissenMai2026/docs/m5-observability.md): M5-Metriken, Logging-Erweiterungen und Dashboard-Konzept
- [docs/operational-drift-dashboard-scope.md](H:/WissenMai2026/docs/operational-drift-dashboard-scope.md): Scope fuer Operational Drift Dashboard, Drift-Metriken und Eskalation
- [docs/postgres-truth-tests.md](H:/WissenMai2026/docs/postgres-truth-tests.md): Wahrheitslogik und Gate-Regeln fuer PostgreSQL-Nachweise inklusive M5-Erweiterung
- [docs/m5-retrieval-quality-baseline.md](H:/WissenMai2026/docs/m5-retrieval-quality-baseline.md): Golden Queries und Retrieval-Qualitaetsmetriken fuer M5
- [docs/retrieval-stability-contract.md](H:/WissenMai2026/docs/retrieval-stability-contract.md): Stabilitaetsvertrag fuer Citation Schema, Ranking, Lifecycle Filtering und Search-vs-Chat-Konsistenz
- [docs/m5-longrun-simulation.md](H:/WissenMai2026/docs/m5-longrun-simulation.md): beschleunigte M5-Langzeitbetriebs-Simulation mit Stop-Kriterien
- [docs/m5-data-aging-entropy-audit.md](H:/WissenMai2026/docs/m5-data-aging-entropy-audit.md): Entropie- und Aging-Audit fuer langlaufende M5-Systeme
- [docs/runbooks/m5-operations-model.md](H:/WissenMai2026/docs/runbooks/m5-operations-model.md): Operations Model, Betriebschecklisten und Eskalationsmodell fuer M5
- [docs/runbooks/m5-drift-repair-strategy.md](H:/WissenMai2026/docs/runbooks/m5-drift-repair-strategy.md): Repair-Strategie, Safety Constraints und Audit-Anforderungen fuer Drift

## Governance Framework

Stand: 2026-05-13

Die folgenden Dokumente bilden das vollstaendige Governance-Framework fuer langfristigen kontrollierten Betrieb. Sie sind verpflichtend fuer alle Architektur-, Schema-, Feature- und Betriebsentscheidungen.

### Architektur- und Schema-Governance

- [docs/architecture-change-governance.md](H:/WissenMai2026/docs/architecture-change-governance.md): Governance fuer Architekturanderungen mit 7 Impact-Bereichen, 4 Pflichtartefakten und verbotenen Mustern
- [docs/schema-evolution-safety-model.md](H:/WissenMai2026/docs/schema-evolution-safety-model.md): Sicherheitsmodell fuer Datenbankschema-Evolution mit Risikoklassen A-D und 11 Schema-Regeln (SE-01 bis SE-11)

### Betrieb und Qualitaet

- [docs/operational-sla-framework.md](H:/WissenMai2026/docs/operational-sla-framework.md): SLA-Framework fuer 8 Betriebsbereiche mit Zielwert, Warnschwelle, kritischer Schwelle und Eskalationskaskade
- [docs/controlled-failure-philosophy.md](H:/WissenMai2026/docs/controlled-failure-philosophy.md): 5 Fehlerprinzipien, standardisierte Fehlercodes, Recovery-Kategorien und Degraded-States
- [docs/frontend-api-unreachable-recovery.md](H:/WissenMai2026/docs/frontend-api-unreachable-recovery.md): API_UNREACHABLE-Recovery-Regeln mit Retry-Strategie und Runtime-Recovery-State-Machine
- [docs/audit-trail-schema.md](H:/WissenMai2026/docs/audit-trail-schema.md): 8 Audit-Event-Typen mit vollstaendigen JSON-Schemas, actor-Feld, Retention-Regeln und Korrelationsanforderungen

### Invarianten und Langzeit

- [docs/system-invariant-registry.md](H:/WissenMai2026/docs/system-invariant-registry.md): Zentrale Registry aller System-Invarianten INV-001 bis INV-036 mit Beschreibung, Criticality, Nachweispflicht und Reparaturpfad
- [docs/long-term-governance-review.md](H:/WissenMai2026/docs/long-term-governance-review.md): Bewertung der 8 Governance-Bereiche (fragmentiert bis systemisch kontrolliert) mit Lueckenanalyse und Langzeitrisiken
- [docs/long-term-architecture-strategy.md](H:/WissenMai2026/docs/long-term-architecture-strategy.md): Mehrjaehrige Architekturstrategie mit 7 strategischen Zielen, 10 No-Go-Verletzungen, Pflicht-Refactoring-Triggern und Feature-Stop-Bedingungen

