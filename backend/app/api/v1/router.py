from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.data_quality import router as data_quality_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.search import router as search_router

router = APIRouter()


@router.get("/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(data_quality_router)
router.include_router(search_router)
router.include_router(chat_router)
router.include_router(admin_router)
router.include_router(jobs_router)
router.include_router(auth_router)

api_router = router
