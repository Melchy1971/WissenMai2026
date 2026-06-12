# Wissensbasis V1

**Status:** BLOCKED (50% progress as of 2026-06-10)

## What it is
Local knowledge base GUI with remote-connected database. Single-user, no auth in V1.

## Stack
- Backend: FastAPI
- Frontend: React/Vite
- DB: PostgreSQL (remote)
- Migrations: Alembic
- Content: Markdown as canonical source

## Milestone Status
| Milestone | Status |
|-----------|--------|
| M3a Frontend Foundation | BLOCKED (NO_GO) — RC stale, regenerate needed |
| M4 Backend | gate_passed (GO) |
| M5 Vorbereitung | gate_passed (GO) |
| M5 Implementierung | BLOCKED |
| M5a Data Quality | BLOCKED |
| M5b Drift | BLOCKED |

## Active Blockers
1. M3a RC stale — run `python scripts/generate_m3a_release_candidate.py`
2. documentation_truth_lint: collected = 0
3. M5a not READY_FOR_M5B
4. m5a_data_quality_gate BLOCKED; report_integrity_v2 BLOCKED

## Repo Location
H:\WissenMai2026
