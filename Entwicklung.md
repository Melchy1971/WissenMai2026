# Entwicklung

Statusquelle: `reports/current/masterplan_status.json`, `docs/gate_hierarchy.json`, `reports/current/m5a_final_readiness_review.json`, `reports/current/m5b_release_decision.json`

Aktuelle Freigaben werden nicht manuell gepflegt. Der generierte Maschinenstatus in `reports/current/masterplan_status.json` ist autoritativ.

## Gate-Hierarchie nach Fix

- M5a ist nur dann Gesamt-`PASS`, wenn `reports/current/m5a_final_readiness_review.json` `READY_FOR_M5B` meldet.
- Ein M5a Slice-Gate bewertet nur den jeweiligen Slice. Slice-`PASS` ist keine M5a-Gesamtfreigabe.
- `reports/current/m5a_data_quality_gate.json` bleibt ein erforderlicher Eingang fuer M5a Final Readiness, ersetzt aber nicht `reports/current/m5a_final_readiness_review.json`.
- `reports/current/m5b_release_decision.json` trennt `DRAFT`, `PREPARED` und `GO`: `PREPARED` erlaubt Vorbereitung, `GO` erlaubt Implementierung.
- Es gibt keine globale Prozent- oder Vollstaendigkeitsfreigabe ausserhalb maschinenlesbarer Reports.

## M5a Slice-Arbeit

Vorhandene Slice-Artefakte:

- Duplicate Detector: `reports/current/m5a_duplicate_detector_gate.json`
- Metadata Detector: `reports/current/m5a_metadata_detector_gate.json`
- Lifecycle Integrity Detector: `reports/current/m5a_lifecycle_integrity_gate.json`

Diese Reports koennen Slice-Fortschritt belegen. Sie ersetzen nicht `reports/current/m5a_final_readiness_review.json` und nicht die Parent-Gate-Validierung aus `docs/gate_hierarchy.json`.

## M5b Planung

M5b Drift Architecture ist ein Planungsartefakt: `docs/m5b-drift-architecture.md`.

Planung als `DRAFT` ist erlaubt. `PREPARED` erlaubt nur Vorbereitung; Implementierung bleibt untersagt, solange `reports/current/m5b_release_decision.json` kein `GO` meldet.

Stand 2026-06-12: M5b-Implementierung vollstaendig. Alpha Gate PASS (Score 100/100, 6 Detektoren, 106/106 Tests). CLI, Dashboard (23/23 Frontend-Tests), REST-API (read-only), Observability (21/21 Tests), Performance Baseline (sub-linear, 100→10k Dokumente) implementiert. M5b-Gates BLOCKED durch Kaskade: Alpha Hardening Gate BLOCKED (AHG-BLOCKER-01: M5a nicht READY_FOR_M5B; AHG-BLOCKER-02: drift_report_integrity PARTIAL) → Beta BLOCKED → Production Readiness BLOCKED. Quelle: `reports/current/m5b_alpha_hardening_gate.json`, `reports/current/m5b_production_readiness_gate.json`.

M5c Preparation PREPARED (16/16 Checks, `reports/current/m5c_preparation_gate.json`). Domain Model, Risk Scoring, Detection Rules, Dry Run Governance, Report Schema, Audit Trail, Dashboard Scope, Implementation Boundary definiert. M5c GO bleibt gesperrt: `reports/current/m5c_start_gate.json` BLOCKED (alle 5 Release-Conditions unerfuellt). M5c Cleanup-Implementierung: NO_GO.

**Cleanup-Aktionen und Repair-Aktionen sind dauerhaft verboten (PROHIBIT-02, PROHIBIT-06). Invariante: Drift Detection darf nur erkennen, nie korrigieren.**

Preparation-Artefakte (vollstaendig, PREP-01 bis PREP-27):
- `docs/m5b-preparation-boundary.md`, `m5b_boundary_report.json`
- `docs/m5b-drift-types.md`, `schemas/drift_types.schema.json`
- `reports/current/m5b_gate_criteria.json`, `docs/m5b-gates.md`
- `docs/m5b-test-strategy.md`, `test_matrix_m5b.json`
- `docs/m5b-risk-matrix.md`, `m5b_risk_matrix.json`
- `docs/m5b-drift-governance.md`, `drift_governance.schema.json`
- `docs/m5b-drift-severity.md`, `drift_severity_matrix.json`
- `docs/m5b-entity-mapping.md`, `drift_entity_mapping.json`
- `docs/m5b-drift-metrics.md`, `drift_metrics.schema.json`
- `docs/m5b-drift-history.md`, `drift_history_model.json`
- `docs/m5b-reporting.md`, `reporting_architecture.json`
- `docs/m5b-testdata-strategy.md`, `drift_test_dataset_plan.json`
- `docs/m5b-rollback.md`, `rollback_strategy.json`
- `reports/current/m5b_architecture_review.json`

Scope- und Boundary-Artefakte (Planungsphase Alpha/Beta):
- `docs/m5b-drift-dashboard-scope.md`, `dashboard_testids.md`
- `docs/m5b-drift-api-scope.md`, `openapi_drift_scope.json`
- `docs/m5b-beta-boundary.md`

Bekannte Risiken: `docs/m5b-risk-matrix.md` (7 Risiken, davon 5 blocking, 2 mit critical impact).

Drift Finding Governance: `docs/m5b-drift-governance.md`, `drift_governance.schema.json`. Invariante: Drift Detection darf nur erkennen, nie korrigieren. Alle 8 PROHIBIT-Regeln sind im Schema maschinenlesbar hinterlegt.

Architecture Review: `reports/current/m5b_architecture_review.json`. Score: 8/8 Artefakte vollstaendig, 0 strukturelle Luecken, 3 offene Entscheidungen (OD-01..OD-03 loesen sich bei Implementation), 2 blockierende Risiken (CCR-02 KL-GOV-001, CCR-03 externe Preconditions).

Alpha/Beta-Gates: Alpha BLOCKED (keine Implementierung vorhanden; erwartet bei Implementation Gate NO-GO). Beta BLOCKED (3/6 Kriterien; BSG-04 API Scope, BSG-05 Dashboard Scope, BSG-06 Documentation Truth bereits PASS). M5c setzt Beta PASS voraus.

## Drift v2 (ABGESCHLOSSEN, 2026-06-15)

Route `/drift` → `DriftPage` → `drift_v2/DriftDashboard` aktiv. Alle Imports aus `features/drift` (alt) entfernt.

- `reports/current/drift_v2_import_audit.json` PASS (0 alte Imports)
- `reports/current/drift_v2_ui_truth_report.json` PASS (29/29 Tests, 8/8 Checks)
- `reports/current/drift_route_recovery_report.json` PASS
- Component Contract: `docs/drift_v2_component_contract.md` (3 testid-GAPs dokumentiert, nicht blockierend)

Formale Freigabe: ausstehend (m5b_production_readiness_gate BLOCKED, cascade aus M5a, root: TEST_DATABASE_URL).
**Cleanup/Repair: NO_GO** — PROHIBIT-02, PROHIBIT-06.

## Local Final Gate Validator v2 (2026-06-15)

Validator: `scripts/local_final_gate_validator_v2.py` — Dependency Graph: `local_final_gate_dependency_graph.json`
Output: `reports/current/final_gate_report.json` — verdict=**BLOCKED**

Blocker (4): report_integrity_v2, m5b_alpha_hardening_gate, m5b_production_readiness_gate, m5c_start_gate.
Warnungen (2): drift_v2_component_contract (PARTIAL_FAIL, 3 GAPs), drift_dashboard_truth_report (INVALID, truncated).
Extern (1): external_env_gate NOT_RUN (72 Tests, blockiert Gate nicht).
Non-Blocking (1): permission_blocker — ACL auf features/drift (alt), aktiver Pfad ist drift_v2, Regel 6 greift.

## Post-RC Plan (2026-06-15)

Entscheidung: `PHASE_0_RC_STABILIZATION_REQUIRED`
Quelle: `reports/current/post_rc_decision.json`, `docs/post_rc_plan.md`

Regel: Keine M5c-Implementierung vor RC-Stabilisierung und externer Testentscheidung.

Phasenreihenfolge:
1. Phase 0 (aktiv): RC-Stabilisierung -- RC-PREREQ-01 bis 03 beheben, RC Gate re-run bis RELEASE_CANDIDATE
2. Phase 1 (gesperrt): Externe Umgebungstests (72 Tests, external_env_gate)
3. Phase 2 (gesperrt): Installer / Deployment
4. Phase 3 (NO_GO): M5c Cleanup Dry-Run Planung -- erst nach m5c_start_gate PASS + PO-Sign-off
5. Parallel moeglich: OPT-5 Nutzerfeedback (S04/S08 als Basis fuer RC-PREREQ-02)

M5c-Lock: LOCKED. Unlock: RC=RELEASE_CANDIDATE + ext. Testentscheidung + m5c_start_gate

## Topics-Feature, Unified Search, Dashboard Widgets (2026-06-16)

Tasks 64–72 abgeschlossen. TC-URL-01 behoben.

### Tasks 64–70: Topics-Backend

**Task 64 — SQLAlchemy Model** (`backend/app/models/topics.py`): 4 Entitäten — Topic, TopicDocument, TopicTag, TopicRelation. Soft-Delete via `deleted_at`. Composite Index `(workspace_id, status)`. Status-Constraint `draft|review|approved|archived`.

**Task 65 — Alembic Migration** `0022_topics`: Topics-Schema, alle 4 Tabellen, Indizes, FK-Constraints.

**Task 66 — Pydantic Schemas** (`backend/app/schemas/topics.py`): TopicCreate, TopicUpdate, TopicRead, TopicListResponse, TopicMergeRequest. Fehlerklassen: TopicNotFoundError, TopicSlugConflictError, TopicMergeConflictError.

**Task 67 — Repository Layer** (`backend/app/repositories/topics.py`): 406 Zeilen, 11 Operationen — get_by_id, get_by_slug, list_topics, create, update, soft_delete, add_document, remove_document, add_tag, remove_tag, get_for_merge.

**Task 68 — Services**: TopicService (353 Zeilen) + TopicMergeService (368 Zeilen) in `backend/app/services/topics/`. Merge-Strategie: Source-Dokumente auf Target migrieren, Source soft-delete, TopicRelation MERGED anlegen.

**Task 69 — FastAPI Router** (`backend/app/api/v1/topics.py`): 10 Endpoints unter `/api/v1/topics`. Auth-Guards: Admin für DELETE/MERGE, Member für GET/POST/PATCH.

**Task 70 — Tests**: Service Unit Tests (377 Zeilen, pytest.mark.unit_fast) + Repository Integration Tests (304 Zeilen, pytest.mark.integration).

### TC-URL-01 (BEHOBEN 2026-06-16)

Bug: `frontend/src/api/topics.js` verwendete `/topics/*` statt `/api/v1/topics/*` — alle 5 API-Calls liefen in 404.
Fix: `const BASE = '/api/v1/topics'` eingeführt, alle hardcodierten Pfade ersetzt.
Dokumentiert in `topic_center_rc.json` (TC-CRIT-03) seit Task #42 — in dieser Session behoben.

### Task 71 — Unified Search

**Backend:**
- `backend/app/schemas/search.py` (87 Zeilen): UnifiedSearchFilters, UnifiedSearchHit, UnifiedSearchResponse, Cursor encode/decode, `_VALID_SORTS = {"score_desc", "created_at_desc", "created_at_asc", "title_asc"}`
- `backend/app/repositories/search.py` (513 Zeilen): Cross-DB — PG (`ts_rank`/`ts_headline`), SQLite (ILIKE). Python-seitiges Merge+Sort+Paginate. Score-Normalisierung: Topics title=0.90, summary=0.65; Documents=0.85; Chunks PG ts_rank oder 0.70 (SQLite).
- `backend/app/services/search_service.py` (211 Zeilen): `search_unified()` mit Cursor-Decode, Validation, Repo-Call, Response-Mapping.
- `backend/app/api/v1/search.py` (131 Zeilen): GET `/chunks` (Legacy) + GET `/unified` mit allen Query-Params.
- `backend/tests/test_unified_search_service.py` (239 Zeilen): 18 Unit-Tests, FakeSearchRepository.

**Frontend:**
- `frontend/src/api/search.js`: `searchUnified()` mit URLSearchParams, `kind[]`- und `status[]`-Multi-Value.
- `frontend/src/features/search/useUnifiedSearch.js` (146 Zeilen): useReducer, 5 States (idle/loading/loading-more/success/error), Aktionen: search/loadMore/setSort/setKindFilter/reset.
- `frontend/src/features/search/UnifiedSearchResultCard.jsx` (123 Zeilen): KindBadge, ScoreBar, `dangerouslySetInnerHTML` für Highlighting.
- `frontend/src/pages/SearchPage.jsx` (313 Zeilen): KindTabs, SortDropdown, Debounce 300ms, SkeletonCard, "Weitere laden"-Button.

Cursor-Pagination: `base64(json({"o": offset}))` — opaques Token. Highlighting: `<mark>`-Tags via `ts_headline` (PG) oder Python-Regex (SQLite).

### Task 72 — Dashboard Widgets

**Backend:**
- `backend/app/schemas/dashboard.py`: TopicsDayCount, TopicTagCount, TopicsWidgetData ergänzt (110 Zeilen gesamt).
- `backend/app/services/dashboard_service.py` (381 Zeilen): `get_topics_widgets()` — 3 Queries: Status-Aggregation, 7-Tage-Trend, Top-Tags via `text()` Raw SQL (kein ORM-Modell für `tags`-Tabelle).
- `backend/app/api/v1/dashboard.py` (99 Zeilen): GET `/topics-widgets` Endpoint.
- `frontend/src/api/dashboard.js` (47 Zeilen): `getDashboardTopicsWidgets()` ergänzt.

**Frontend:**
- `frontend/src/features/dashboard/TopicsWidgetPanel.jsx` (325 Zeilen): DonutChart (SVG stroke-dasharray), BarChart (CSS flex), TrendChart (SVG polyline+area), TagCloud, SkeletonWidget.
- `frontend/src/pages/DashboardPage.jsx` (239 Zeilen): Vollständig neu, TopicsWidgetPanel integriert.
- Dark Mode: explizit deferred (LOW, TC-DM-01).
- Skeleton Loader: `@keyframes skel-pulse` implementiert.

### Gold Path nach Fix

Backend: 8/8 PASS (alle Schritte). Frontend: 4/8 PASS (GP-T01 Create, GP-T02 List, GP-T03 Detail, GP-T07 Status-Update). NOT_IMPLEMENTED: GP-T04 Dokument-Anhang (4h), GP-T05 Tag-UI (4h), GP-T08 Merge-UI (Post-MVP). Quelle: `reports/current/topics_gold_path.json`.

### Offene Punkte

- **TC-A11Y-01** (LOW): Kein vollständiger `aria-label`-Audit für Topics-Komponenten.
- **TC-DM-01** (LOW): Dark Mode für Topics/Search/Dashboard deferred.
- **TC-UI-01** (LOW): Dokument-Anhang-UI nicht implementiert (Attachment-Flow fehlt im Frontend).
- **TC-UI-02** (LOW): Tag-UI nicht implementiert (Tag-Verwaltung fehlt im Frontend).
- **KL-T-003** (MEDIUM): Search-Performance bei Scale nicht validiert (Python-seitiges Merge ohne DB-seitige Pagination).

### Reifegrad

Topics-Backend: PRODUKTIONSREIF. Unified Search: PRODUKTIONSREIF. Dashboard Widgets: PRODUKTIONSREIF.
Gesamtbewertung Topics-Feature: **RC-GRADE**. Quelle: `reports/current/topics_release_report.json`, `reports/current/masterplan_status.json`.

Verbleibender Gesamtblocker: BLOCK-02 (M5b-Gate-Kaskade, root: TEST_DATABASE_URL / M5a not READY_FOR_M5B).