"""Collaboration-Endpunkte: teams, runs, conflicts."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_workspace_member, AuthContext

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

_teams: list[dict] = []
_runs: list[dict] = []
_conflicts: list[dict] = []


@router.get("/teams")
def list_teams(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _teams, "total": len(_teams)}


@router.get("/runs")
def list_runs(
    limit: int = 50,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    # Shared Workspace zeigt keine SECRET-Daten
    safe_runs = []
    for run in _runs[-limit:]:
        safe_run = dict(run)
        if "shared_workspace_snapshot" in safe_run:
            safe_run["shared_workspace_snapshot"] = [
                item for item in safe_run["shared_workspace_snapshot"]
                if item.get("classification") != "SECRET"
            ]
        safe_runs.append(safe_run)
    return {"items": safe_runs, "total": len(_runs)}


@router.get("/conflicts")
def list_conflicts(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _conflicts, "total": len(_conflicts)}
