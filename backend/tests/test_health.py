import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.observability.middleware import PrometheusMetricsMiddleware
from app.observability.prometheus_metrics import metrics_response


def test_app_is_importable() -> None:
    module = importlib.import_module("app.main")

    assert module.app is not None


def test_health_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_returns_prometheus_text() -> None:
    from app.main import app

    client = TestClient(app)
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert "application/json" not in response.headers["content-type"]
    assert "http_requests_total" in response.text or "app_info" in response.text


def test_metrics_use_route_templates_without_technical_ids() -> None:
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware)

    @app.get("/metric-test/items/{item_id}")
    def get_item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    technical_id = "00000000-0000-0000-0000-000000000101"
    TestClient(app).get(f"/metric-test/items/{technical_id}?trace_id={technical_id}")
    content, _ = metrics_response()
    metrics_text = content.decode("utf-8")

    assert technical_id not in metrics_text
    assert 'path="/metric-test/items/{item_id}"' in metrics_text


def test_database_health_reports_missing_configuration(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", None)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "SERVICE_UNAVAILABLE",
            "message": "DATABASE_URL is not configured",
            "details": {},
        }
    }
