from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.data_quality import router as data_quality_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.search import router as search_router

# GUI-Erweiterungen
from app.api.v1.status import router as status_router
from app.api.v1.settings import router as settings_router
from app.api.v1.security import router as security_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.audit import router as audit_router
from app.api.v1.governance import router as governance_router
from app.api.v1.agents_gui import router as agents_gui_router
from app.api.v1.collaboration_gui import router as collaboration_router
from app.api.v1.rag_gui import router as rag_gui_router
from app.api.v1.drift import router as drift_router
from app.api.v1.memory import router as memory_router
from app.api.v1.topics import router as topics_router
from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.tools import router as tools_router

router = APIRouter()


@router.get("/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


# Existing
router.include_router(data_quality_router)
router.include_router(search_router)
router.include_router(chat_router)
router.include_router(admin_router)
router.include_router(jobs_router)
router.include_router(auth_router)
router.include_router(analysis_router)

# GUI
router.include_router(status_router)
router.include_router(settings_router)
router.include_router(security_router)
router.include_router(approvals_router)
router.include_router(audit_router)
router.include_router(governance_router)
router.include_router(agents_gui_router)
router.include_router(collaboration_router)
router.include_router(rag_gui_router)
router.include_router(dashboard_router)
router.include_router(tools_router)
router.include_router(memory_router)
router.include_router(tasks_router)
router.include_router(projects_router)
router.include_router(orchestrator_router)

# Drift Detection — read-only
router.include_router(drift_router)

# Topics
router.include_router(topics_router)

api_router = router
