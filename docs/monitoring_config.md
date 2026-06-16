# Monitoring Konfiguration

Stand: 2026-06-15
Quelle: `reports/current/observability_report.json`

## Backend

### Implementiert

| Komponente | Datei | Status |
|---|---|---|
| Structured JSON Logging | `app/observability/logging.py` | AKTIV |
| Correlation-ID pro Request | `app/observability/middleware.py` (`CorrelationIdMiddleware`) | AKTIV |
| Auth-Context (workspace_id, user_id) | `app/observability/middleware.py` (`AuthContextMiddleware`) | AKTIV |
| Import Job Events | `app/observability/logging.py` (`log_import_event`) | AKTIV |
| Drift Run Metriken | `app/observability/drift_metrics.py` | AKTIV |
| M5 Metric Definitions | `app/observability/m5_metrics.py` | AKTIV |
| Credential Redaction | `app/core/redaction.py` | AKTIV |
| MetricsRegistry (In-Memory) | `app/observability/logging.py` | AKTIV |

### Fehlend — Implementierungsbedarf

#### 1. Request Access Log Middleware

```python
# app/observability/request_log_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from app.observability.logging import log_event
import time

SKIP_PATHS = {"/health", "/health/db", "/openapi.json", "/docs", "/redoc"}

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - t0) * 1000)
        log_event(
            "api_request",
            status="success" if response.status_code < 400 else "error",
            duration_ms=duration_ms,
            error_code=str(response.status_code) if response.status_code >= 400 else None,
        )
        return response
```

Registrierung in `app/main.py` nach `CorrelationIdMiddleware`:
```python
from app.observability.request_log_middleware import RequestLogMiddleware
app.add_middleware(RequestLogMiddleware)
```

#### 2. Auth Failure Counter

`AuthContextMiddleware._error_response()` muss `log_event` aufrufen:

```python
from app.observability.logging import log_event

def _error_response(self, error) -> JSONResponse:
    if error.status_code in (401, 403):
        log_event(
            "auth_failure",
            status="failed",
            error_code=error.code,
        )
    return JSONResponse(
        status_code=error.status_code,
        content=error_content(error.code, error.message, error.details),
    )
```

#### 3. Analysis Job Metriken

```python
# app/observability/analysis_metrics.py
from app.observability.logging import log_event, metrics_registry

def record_analysis_job_started(*, job_id: str, workspace_id: str, job_type: str) -> None:
    log_event("analysis_job_started", status="started",
              job_id=job_id, workspace_id=workspace_id, event_type=job_type)

def record_analysis_job_completed(*, job_id: str, workspace_id: str, duration_ms: int) -> None:
    log_event("analysis_job_completed", status="completed",
              job_id=job_id, workspace_id=workspace_id, duration_ms=duration_ms)

def record_analysis_job_failed(*, job_id: str, workspace_id: str, error_code: str) -> None:
    log_event("analysis_job_failed", status="failed",
              job_id=job_id, workspace_id=workspace_id, error_code=error_code)
```

Einbinden in `app/services/analysis/service.py` an den Job-Status-Transitionen.

### Log-Felder pro Event-Typ

| Event | Felder | VERBOTEN |
|---|---|---|
| `api_request` | method, path, status_code, duration_ms, correlation_id | Auth-Header, Token, Body |
| `auth_failure` | error_code, correlation_id, workspace_id | Token, Password, Bearer-Value |
| `import_job_*` | job_id, document_id, workspace_id, parser_type, chunk_count, duration_ms | Dokumentinhalt, Dateiname |
| `analysis_job_*` | job_id, workspace_id, job_type, duration_ms, error_code | Query-Inhalt, Ergebnisinhalt |
| `drift_run_*` | drift_run_id, workspace_id, findings_count, critical_findings_count, duration_ms | Dokumentinhalt, Field-Values |

### Gesichert nicht geloggt

- Credentials: durch `app/core/redaction.py` (`SECRET_FIELD_NAMES`, `SECRET_PATTERNS`)
- Tokens: `AuthContextMiddleware` liest Token aus Header, gibt ihn nie an Log weiter
- Dokumentinhalte: `drift_metrics.py` `_SAFE_FIELDS` whitelisted nur sichere Felder
- `apiClient.js`: Result-Pattern gibt nur `code`, `message`, `status` weiter — kein Request-Body

---

## Frontend

### Implementiert

| Komponente | Datei | Status |
|---|---|---|
| API Result-Pattern | `src/lib/apiClient.js` | AKTIV |
| API Error-Normalisierung | `src/api/client.js` (`ApiClientError`) | AKTIV |

### Fehlend — Implementierungsbedarf

#### 1. Error Boundary (React)

```jsx
// frontend/src/components/ErrorBoundary.jsx
import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorId: null };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    const errorId = crypto.randomUUID();
    // KEIN Stack-Trace mit Nutzdaten loggen
    console.error(JSON.stringify({
      event: 'ui_error',
      errorId,
      message: error.message,
      componentStack: info.componentStack?.split('\n').slice(0, 5).join(' | '),
    }));
    this.setState({ errorId });
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? <p>Ein Fehler ist aufgetreten (ID: {this.state.errorId})</p>;
    }
    return this.props.children;
  }
}
```

Einbinden in `App.jsx` oder je Page-Komponente:
```jsx
<ErrorBoundary fallback={<ErrorPage />}>
  <RouterProvider router={router} />
</ErrorBoundary>
```

#### 2. API Failure Logger

In `src/lib/apiClient.js` ergaenzen:

```js
function logApiFailure({ path, code, status }) {
  // Kein Auth-Header, kein Token, kein Body
  console.error(JSON.stringify({
    event: 'api_failure',
    path,
    code,
    status,
    ts: new Date().toISOString(),
  }));
}

export async function callApi(path, options = {}) {
  try {
    const data = await requestJson(path, options);
    return { ok: true, data };
  } catch (err) {
    if (err instanceof ApiClientError) {
      logApiFailure({ path, code: err.code, status: err.status });
      return { ok: false, error: { code: err.code, message: err.message, status: err.status } };
    }
    logApiFailure({ path, code: 'UNKNOWN_ERROR', status: null });
    return { ok: false, error: { code: 'UNKNOWN_ERROR', message: String(err), status: null } };
  }
}
```

#### 3. Route Error Handler

In `src/router.jsx` (oder Vite Router-Konfiguration):

```jsx
function RouteErrorPage() {
  const error = useRouteError();
  console.error(JSON.stringify({
    event: 'route_error',
    status: error?.status,
    message: error?.statusText ?? error?.message,
  }));
  return <ErrorPage status={error?.status} />;
}

// In createBrowserRouter:
{ path: '*', errorElement: <RouteErrorPage /> }
```

---

## Metriken-Uebersicht (Soll-Zustand)

| Metrik | Typ | Backend | Frontend |
|---|---|---|---|
| `api_request.success` | Counter | RequestLogMiddleware (FEHLT) | -- |
| `api_request.error` | Counter | RequestLogMiddleware (FEHLT) | api_failure log |
| `auth_failure.failed` | Counter | AuthContextMiddleware (FEHLT) | -- |
| `import_job_started.started` | Counter | log_import_event (AKTIV) | -- |
| `import_job_completed.completed` | Counter | log_import_event (AKTIV) | -- |
| `import_job_failed.failed` | Counter | log_import_event (AKTIV) | -- |
| `analysis_job_started.started` | Counter | analysis_metrics.py (FEHLT) | -- |
| `analysis_job_completed.completed` | Counter | analysis_metrics.py (FEHLT) | -- |
| `analysis_job_failed.failed` | Counter | analysis_metrics.py (FEHLT) | -- |
| `drift_run_started.started` | Counter | drift_metrics.py (AKTIV) | -- |
| `drift_run_completed.completed` | Counter | drift_metrics.py (AKTIV) | -- |
| `drift_run_failed.failed` | Counter | drift_metrics.py (AKTIV) | -- |
| `ui_error` | Event | -- | ErrorBoundary (FEHLT) |
| `route_error` | Event | -- | RouteErrorPage (FEHLT) |

Metriken-Snapshot abrufbar ueber `metrics_registry.snapshot()` (In-Memory).
Fuer persistente Metriken: Prometheus-Exporter oder Export-Endpoint `/api/v1/admin/metrics` (noch nicht implementiert).
