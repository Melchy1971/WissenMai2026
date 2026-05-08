from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.documents import router as documents_router
from app.api.error_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.observability.logging import configure_structured_logging
from app.observability.auth_middleware import AuthContextMiddleware
from app.observability.middleware import CorrelationIdMiddleware

app = FastAPI(title="Wissensbasis API", version="0.1.0")
configure_structured_logging()
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(api_router, prefix="/api/v1")
