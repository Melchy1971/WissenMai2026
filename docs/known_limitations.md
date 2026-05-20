# Known Limitations Register

Stand: 2026-05-20

Ziel: Offene Punkte werden nach Gate-Wirkung getrennt. Nicht jede Limitation blockiert denselben Gate.

Maschinenlesbare Quelle: `docs/known_limitations.json`.

## Kategorien

1. M3a blocker
2. M4 blocker
3. M5 blocker
4. non-blocking debt
5. explicitly deferred

## Register

| ID | Kategorie | Bereich | Beschreibung | Blockiert Gate? | Risiko | Workaround | Zielphase | Review Datum |
|---|---|---|---|---|---|---|---|---|
| KL-M4-001 | M4 blocker | M4 Truth / PostgreSQL | PostgreSQL-Truth ist nicht gruen: 138 collected, 120 passed, 16 failed, 2 errors, exit_code 1. | m4_overall_gate, m5_start_gate | M4 kann nicht gate_passed werden; M5 darf nicht starten. | M4-Truth-Fehler beheben und Report neu erzeugen. | M4 | 2026-05-27 |
| KL-M4-002 | M4 blocker | M4b Upload/Queue | M4b-kritischer Truth-Test fuer stale import job recovery ist rot. | m4b_gate, m4_overall_gate | Upload-/Queue-Recovery ist nicht belastbar freigegeben. | Recovery-Pfad isoliert fixen und gegen echte PostgreSQL-DB validieren. | M4b | 2026-05-27 |
| KL-M4-003 | M4 blocker | Report Integrity | PostgreSQL Truth enthaelt 2 Setup-/Collect-Errors. | m4_overall_gate, m5_start_gate | Unbekannte Setupfehler koennen echte Regressionen verbergen. | Setup-/Collect-Fehler isolieren und beheben. | M4 | 2026-05-27 |
| KL-M4-004 | M4 blocker | Gate Reporting | Split-Reports fuer M4a, M4b, M4c, M4e und M4 Gesamt fehlen. | m4a_gate, m4b_gate, m4c_gate, m4e_gate, m4_overall_gate | Neue Gate-Hierarchie kann M4 nicht maschinenlesbar freigeben. | Split-Reports erzeugen und Gate-Hierarchie auswerten. | M4 | 2026-05-27 |
| KL-M5-001 | M5 blocker | M5 Transition | M5 Startgate bleibt blockiert, solange M4 Gesamtgate nicht PASS ist. | m5_start_gate, operational_governance_gate | M5 wuerde auf nicht freigegebener M4-Basis starten. | M5 nur konzeptionell vorbereiten. | M5 | 2026-05-27 |
| KL-M5-002 | M5 blocker | M5 Entropy/Drift | 15 M5 Entropy-/Drift-Failures im aktuellen PostgreSQL-Truth-Kontext. | m5_start_gate | Langzeitbetrieb und Drift-Recovery sind nicht freigegeben. | Nach M4 PASS gezielt M5-Truth-Suite reparieren. | M5 | 2026-06-03 |
| KL-M5-003 | M5 blocker | Operational Governance | Governance Gate darf erst nach M5 Startgate blockierend bewertet werden. | operational_governance_gate | Governance-Findings koennten zu frueh M4 blockieren. | Governance-Reports erst nach M5 Startgate blockierend nutzen. | M5 | 2026-06-03 |
| KL-NB-001 | non-blocking debt | M3a Evidence Drift | Finaler M3a-Gate-Report referenziert 82/82; aktueller Frontend Truth ist 100/100. | nein | Manuelle Auswertung kann verwirrt werden. | Aktuellen frontend_truth_report direkt zitieren. | M3a documentation maintenance | 2026-05-27 |
| KL-NB-002 | non-blocking debt | M4e Backup/Restore | M4e Minimal ist dokumentiert, Produktionshaertung bleibt offen. | nein | Minimalpfad ist belegt, Betriebsqualitaet aber nicht voll gehaertet. | Nur Minimalpfad freigeben; Operations-Haertung spaeter. | M5 Operations | 2026-06-03 |
| KL-NB-003 | non-blocking debt | M4d Diagnostics | M4d ist read-only; mutierende Admin-Aktionen bleiben blockiert. | nein | Operatoren koennen nicht aus der UI reparieren. | Runbooks/CLI verwenden; M5-Governance abwarten. | M5 Operations | 2026-06-03 |
| KL-NB-004 | non-blocking debt | API Versioning | `/api/v1/documents` Alias ist nicht durchgaengig konsolidiert. | nein | Spaetere Clients koennen an uneinheitliche Pfade koppeln. | API-Vertrag vor neuer Clientbindung pruefen. | M4/M5 API hardening | 2026-06-03 |
| KL-DEF-001 | explicitly deferred | OCR | OCR fuer gescannte PDFs ist nicht Teil des aktuellen Gates. | nein | Gescannte PDFs sind fuer Suche/Chat nicht nutzbar. | `OCR_REQUIRED` sichtbar halten; OCR separat planen. | Post-M4 feature | 2026-06-17 |
| KL-DEF-002 | explicitly deferred | Embeddings/Vektorsuche | Embeddings und Vektorsuche sind optional und nicht V1-kritisch. | nein | Semantische Suche bleibt begrenzt. | FTS-/Retrieval-Baseline weiter nutzen. | Post-V1 or M5+ | 2026-07-01 |
| KL-DEF-003 | explicitly deferred | Analyse/Merge/Refine | Analyse-, Merge- und Refine-Fachlogik ist vorbereitet, aber nicht umgesetzt. | nein | Erweiterte Wissensbearbeitung fehlt. | Als eigenes Feature planen. | Post-M4 feature | 2026-07-01 |
| KL-M3A-001 | M3a blocker | M3a Gate | Kein aktueller M3a-Blocker bekannt; M3a RC steht auf GO. | nein | Neue rote M3a-Reports koennen M3a wieder blockieren. | Vor neuen Freigabeaussagen aktuelle Reports pruefen. | M3a maintenance | 2026-05-27 |

## Gate-Regel

- M3a wird nur durch M3a-relevante Reports blockiert.
- M4 wird durch M4a/b/c/e und M4-Truth blockiert, nicht durch M5- oder Governance-Findings.
- M5 wird erst nach M4 Gesamtgate bewertet.
- Governance blockiert erst nach M5 Startgate.
