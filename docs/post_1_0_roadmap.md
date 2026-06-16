# Post-1.0 Roadmap

Stand: 2026-06-15
Voraussetzung: Version 1.0 APPROVED (`reports/current/version_1_0_decision.json`)
Quelle: `reports/current/masterplan_status.json`, `reports/current/known_limitations.json`, `docs/post_rc_plan.md`

Invarianten (unveraenderlich fuer alle Phasen):
- PROHIBIT-02: Kein RepairButton
- PROHIBIT-06: Kein CleanupButton
- PROHIBIT-08: Keine automatische M5c-Ausfuehrung ohne PO-Approval je Proposal
- Drift Detection: Read-Only bis M5c GO + PO-Sign-off

---

## Phase 1: M5c Cleanup Dry Run

**Voraussetzungen:**
- Version 1.0 APPROVED
- `m5c_start_gate` = PASS (aktuell BLOCKED, 5/5 Release-Conditions unerfuellt)
- PO-Sign-off je Proposal (PROHIBIT-08)
- Externes Test-Ergebnis vorliegt

**Nutzen:**
- Datenqualitaet verbessern: Identifizierte Drift-Findings koennen kontrolliert behoben werden
- M5c Preparation ist vollstaendig (16/16 Checks PASS, `m5c_preparation_gate.json`)
- Domain Model, Risk Scoring, Detection Rules, Dry Run Governance bereits definiert

**Risiken:**
- Mutierende Aktionen ohne vollstaendige Gate-Kaskade koennen Datenzustand korrumpieren
- PROHIBIT-02/06/08 muessen per Gate-Check vor jedem Cleanup-Lauf verifiziert werden
- KL-GOV-001: Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt (bleibt bis Gate-PASS riskant)
- Dry Run bedeutet: kein tatsaechliches Schreiben — nur Simulation und Protokollierung

**Aufwand:** Mittel (2-3 Wochen)
- m5c_start_gate deblocken: Release-Conditions 1-5 erfuellen
- PO-Review-Prozess fuer jedes Cleanup-Proposal etablieren
- Dry-Run-Governance-Workflow implementieren (Audit Trail, Rollback-Plan)

---

## Phase 2: M5d Repair Governance

**Voraussetzungen:**
- Phase 1 abgeschlossen (M5c Dry Run PASS, kein Datenverlust)
- PO-Sign-off fuer Repair-Aktionen
- Audit-Trail-System produktiv
- Rollback-Strategie getestet (`docs/m5b-rollback.md` als Basis)

**Nutzen:**
- Drift-Findings koennen nicht nur erkannt, sondern gezielt korrigiert werden
- Schliesst den Governance-Zyklus: Erkennen → Bewerten → Korrigieren → Verifizieren
- Reduziert manuellen Aufwand bei wiederkehrenden Datenqualitaetsproblemen

**Risiken:**
- Repair-Aktionen sind irreversibel ohne Backup — Backup/Restore-Prozess muss 100% zuverlaeassig sein
- Fehlklassifikation durch Drift-Detektoren kann zu falschen Repairs fuehren
- Multi-User-Konflikte: gleichzeitige Repair-Aktionen koennen sich ueberschneiden
- KL-M5-T-001/002: Drift-Truth-Failures und fehlende Slice-Artefakte erhoehen Fehlerrisiko

**Aufwand:** Hoch (4-6 Wochen)
- Repair-API-Endpoints (Schreib-Operationen) mit vollstaendiger Governance
- PO-Approval-Workflow UI
- Conflict-Detection fuer gleichzeitige Repairs
- Rollback-Mechanismus fuer jeden Repair-Typ

---

## Phase 3: Governance Automation

**Voraussetzungen:**
- Phase 2 abgeschlossen (Repair-Prozess stabil, > 30 Tage produktiv ohne Datenverlust)
- Audit-Trail-Daten aus Phase 1+2 als Trainingsgrundlage

**Nutzen:**
- Wiederkehrende, risikoarme Governance-Aufgaben automatisieren
- Reduktion manueller PO-Reviews fuer Standard-Faelle (definierbare Schwellenwerte)
- Betriebskosten sinken durch weniger manuelle Eingriffe
- Governance-Reports automatisch generieren (taeglich/woechentlich)

**Risiken:**
- Automation kann menschliche Kontrolle ersetzen, bevor das System ausreichend erprobt ist
- False-Positive-Rate der Detektoren muss unter Schwellenwert liegen (aus Phase 1+2 messbar)
- Regulatory-Risiko: automatisierte Datenmanipulation ohne Nachvollziehbarkeit
- Systemkomplexitaet steigt erheblich (neue Failure-Modi)

**Aufwand:** Hoch (6-8 Wochen)
- Regelbasierte Automation-Engine (konfigurierbares Ruleset)
- PO-Override-Mechanismus (jederzeit abbrechbar)
- Monitoring-Erweiterung fuer Automation-Laeufe
- Compliance-Report-Generator

---

## Phase 4: Performance Optimierung

**Voraussetzungen:**
- Version 1.0 produktiv (Baseline-Metriken aus Live-Betrieb vorhanden)
- Performance Smoke Test PASS mit konkreten p50/p95-Messwerten
- N+1-Query-Analyse abgeschlossen

**Nutzen:**
- API-Antwortzeiten unter definierten SLA-Schwellenwerten
- Skalierbarkeit fuer steigende Dokumentanzahl (100k+)
- Frontend-Ladezeit unter 2s (Cold Load)
- Drift-CLI unter 10s fuer typische Workloads

**Risiken:**
- Vorzeitige Optimierung ohne Messdaten fuehrt zu falschem Fokus
- Cache-Schichten erhoehen Komplexitaet und Inkonsistenzrisiko
- Index-Aenderungen in PostgreSQL koennen Migrationen erfordern

**Aufwand:** Mittel (2-4 Wochen, iterativ)
- N+1-Queries identifizieren und beheben (SQLAlchemy selectinload/joinedload)
- PostgreSQL-Indizes optimieren (EXPLAIN ANALYZE)
- API-Response-Caching fuer read-heavy Endpoints
- Vite-Bundle-Splitting fuer Frontend-Ladezeit
- Drift-CLI: Parallelisierung der Detektoren (asyncio oder multiprocessing)

---

## Phase 5: Multi-User Ausbau

**Voraussetzungen:**
- Version 1.0 produktiv (Single-Workspace stabil)
- Workspace-Isolation verifiziert (External Env Tests IC-05 PASS)
- Backup/Restore-Prozess fuer Multi-Workspace getestet

**Nutzen:**
- Mehrere Teams koennen die Plattform gleichzeitig und isoliert nutzen
- Self-Service-Onboarding neuer Workspaces ohne Admin-Eingriff
- Nutzerfeedback aus Pilotgruppen fliesst in Iteration ein

**Risiken:**
- Workspace-Isolation-Fehler koennen Datenlecks zwischen Teams verursachen
- Datenbankschema muss workspace_id konsequent in allen Queries durchsetzen
- Auth-Skalierung: Token-Validierung unter Last (Connection-Pool)
- CORS-Konfiguration fuer Multi-Domain-Setups

**Aufwand:** Hoch (4-6 Wochen)
- Workspace-Onboarding-API und UI
- Admin-Console fuer Workspace-Management
- Multi-Workspace-Lasttests
- Workspace-Quota-Management (Dokumente, Jobs)
- Erweiterung des External Env Testplans um Multi-Workspace-Szenarien

---

## Phase 6: Erweiterte KI Analyse

**Voraussetzungen:**
- Phase 4 abgeschlossen (Performance-Baseline stabil)
- KL-DEF-002 adressiert: Embeddings/Vektorsuche entschieden
- AI-Provider-Vertrag und Datenschutz-Assessment abgeschlossen

**Nutzen:**
- Semantische Suche ersetzt keyword-basierte Suche
- Automatische Themen-Extraktion und Verschlagwortung
- Aehnlichkeits-Erkennung zwischen Dokumenten (Duplikat-Erkennung Phase 2)
- Erweiterte RAG-Faehigkeiten fuer komplexe Analysen
- OCR fuer gescannte PDFs (KL-DEF-001 schliessen)

**Risiken:**
- AI-Provider-Abhaengigkeit: Ausfall oder Preisaenderung trifft Kernfunktionen
- Embeddings in PostgreSQL (pgvector) erhoehen Storage-Anforderungen erheblich
- Halluzinationen in generativen Antworten erfordern Nutzer-Transparenz
- DSGVO: Dokumentinhalte gehen an externen Provider — Datenschutz-Assessment erforderlich

**Aufwand:** Sehr hoch (8-12 Wochen)
- pgvector-Extension und Embedding-Pipeline
- OCR-Integration (Tesseract oder Cloud-OCR)
- Semantische Such-API und Frontend-Integration
- Provider-Abstraktion (Austauschbarkeit sicherstellen)
- Evaluation-Framework fuer AI-Qualitaet

---

## Phasen-Uebersicht

| Phase | Nutzen | Aufwand | Voraussetzung |
|---|---|---|---|
| 1. M5c Cleanup Dry Run | Datenmutationen kontrolliert freigeben | Mittel (2-3 W) | V1.0 + m5c_start_gate PASS + PO-Sign-off |
| 2. M5d Repair Governance | Vollstaendiger Governance-Zyklus | Hoch (4-6 W) | Phase 1 stabil |
| 3. Governance Automation | Betriebskosten senken | Hoch (6-8 W) | Phase 2 > 30 Tage produktiv |
| 4. Performance Optimierung | SLA-faehige Antwortzeiten | Mittel (2-4 W) | Live-Metriken vorhanden |
| 5. Multi-User Ausbau | Mehrere Teams parallel | Hoch (4-6 W) | Workspace-Isolation verifiziert |
| 6. Erweiterte KI Analyse | Semantische Suche, OCR, RAG | Sehr hoch (8-12 W) | Phase 4 + Datenschutz-Assessment |

Empfohlene Parallelisierung: Phase 4 kann parallel zu Phase 2 oder 3 laufen (unabhaengige Codebase-Bereiche). Phasen 1-3 sind sequenziell (jede baut auf der vorherigen auf). Phase 5 und 6 koennen nach Phase 4 parallel gestartet werden.
