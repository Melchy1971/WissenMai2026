# Ruflo — Wissensbasis V1

**Interner Produktname:** Ruflo  
**Status:** BLOCKED — NOT_READY_FOR_1_0 (Stand: 2026-06-15)  
**Produktreife-Score:** 52/85 (Schwellwert für 1.0-Release: 85)

## Stack

- Backend: FastAPI
- Frontend: React + Vite
- DB: PostgreSQL
- Migrations: Alembic
- LLM: Ollama (lokal, HTTP POST http://localhost:11434/api/generate)
- Repo: H:\WissenMai2026

## API-Architektur (wichtig!)

- `documents_router` gemountet bei `/` mit prefix `/documents` → Endpunkte unter `/documents/*` (KEIN /api/v1/-Präfix)
- `api_router` bei `/api/v1` → Analysis, Topics, Search, Dashboard, Export

## Aktueller Zustand (Stand 2026-06-15, nach Reports #48–#57)

| Bereich | Status |
|---------|--------|
| Dashboard | CONDITIONAL_PASS — W06 Drift fehlt (Backend), W07 unklar |
| Dokumente | TEILWEISE — Kern vollständig; Tags/Themen fehlen; tech. IDs in DocumentMetaCard sichtbar |
| Import | VOLLSTÄNDIG (Retry-Button im Frontend fehlt noch) |
| Suche | TEILWEISE — Chunk-Volltext funktioniert; Tag-/Themen-Suche fehlt |
| Themen | NICHT_PRODUKTIONSREIF — Backend vollständig fehlend |
| Datenanalyse | NICHT_PRODUKTIONSREIF — Backend vollständig, AnalysisPage.jsx fehlt |
| Export | NICHT_IMPLEMENTIERT — vollständig fehlend |
| Benutzerverwaltung | VOLLSTÄNDIG |

## Primäre Blocker (für 1.0)

| ID | Bereich | Root Cause |
|----|---------|------------|
| B01 | Topics/Themenzentrum | P1-GAP-01 (ORM) + P1-GAP-02 (API) + URL-Bug in topics.js |
| B02 | Datenanalyse Frontend | AGAP-07: AnalysisPage.jsx nicht implementiert |
| B03 | Export Center | Vollständig fehlend — kein Backend, kein Frontend |
| B04 | Dashboard W06 Drift | GET /api/v1/dashboard/drift fehlt |
| B05 | Cancel Endpunkt | AGAP-02: POST /analysis/jobs/:id/cancel fehlt |
| DC-F01 | Dok-Center | UUIDs (id, workspaceId, ownerUserId) in DocumentMetaCard sichtbar |

## Gate-Ergebnisse (aktuell)

- `product_release_gate.json`: BLOCKED — 5/7 Gates blockiert
- `product_e2e_truth_suite.json`: FAIL — 5/9 Szenarien FAIL
- `product_gold_path.json`: FAIL — 3/8 Schritte PASS
- `version_1_0_candidate_gate.json`: BLOCKED — 3/4 Conditions FAIL
- `version_1_0_scope_freeze.md`: PASS — dokumentiert

## Sprint-Plan

- `docs/product_gap_sprint.md` — 1 Woche, Solo, Ollama lokal
- `tasks/product_gap_tasks.md` — 39 Tasks (T01–T39)
- Erwartung nach Sprint: Produktreife ~78–82 (knapp unter 85-Schwellwert)
- Für 85 zusätzlich nötig: Lazy Loading, KWIC, deutsches FTS-Stemming, AGAP-02 Cancel, Tags vollständig

## Security-Constraints (unveränderlich)

- PROHIBIT-02: Kein RepairButton (nirgends)
- PROHIBIT-06: Kein CleanupButton (nirgends)
- PROHIBIT-08: Keine automatische M5c-Ausführung — Approval immer manuell
- M5c: NO_GO bis m5c_start_gate = PASS und PO-Sign-off
- Drift: Read-Only — kein Schreiben, kein Reparieren, kein Bereinigen
- Kein Credential-/Token-Logging, keine .env-Commits

## Reports (aktuell, alle in reports/current/)

document_center_product_ready.json, document_preview_ready.json, topic_center_product_ready.json,
search_experience_ready.json, export_center_product_ready.json, analysis_ux_ready.json,
product_gold_path.json, product_maturity_v2.json, version_1_0_candidate_gate.json,
product_release_gate.json, product_e2e_truth_suite.json
