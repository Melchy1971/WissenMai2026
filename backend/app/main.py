from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.documents import router as documents_router
from app.api.error_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.observability.logging import configure_structured_logging
from app.observability.auth_middleware import AuthContextMiddleware
from app.observability.middleware import CorrelationIdMiddleware


@asynccontextmanager
async def _lifespan(application: FastAPI):  # noqa: ARG001
    """Run preflight checks at startup. Fail-fast in production."""
    from app.services.preflight import PreflightService
    PreflightService().run_or_raise()
    yield


app = FastAPI(title="Wissensbasis API", version="0.1.0", lifespan=_lifespan)
configure_structured_logging()
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://127.0.0.1:5173",
		"http://localhost:5173",
		"http://127.0.0.1:5174",
		"http://localhost:5174",
		"http://127.0.0.1:5175",
		"http://localhost:5175",
		"http://127.0.0.1:5176",
		"http://localhost:5176",
		"http://127.0.0.1:7473",
		"http://localhost:7473",
		"http://127.0.0.1:7474",
		"http://localhost:7474",
		"http://127.0.0.1:7475",
		"http://localhost:7475",
		"http://127.0.0.1:7476",
		"http://localhost:7476",
	],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(api_router, prefix="/api/v1")
