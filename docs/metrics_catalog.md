# Metrics Catalog — PRI-7

Stand: 2026-06-17
Quelle: `reports/current/observability_report.json`

---

## System-Metriken

| Name | Einheit | Quelle |
|------|---------|--------|
| cpu_usage_percent | % | psutil |
| memory_usage_mb | MB | psutil |
| disk_usage_percent | % | psutil |

---

## Application-Metriken

| Name | Labels | Typ |
|------|--------|-----|
| http_requests_total | method, path, status_code | Counter |
| http_request_duration_seconds | method, path | Histogram |
| job_queue_depth | job_type | Gauge |
| job_success_total | job_type | Counter |
| job_failure_total | job_type | Counter |
| provider_request_duration_seconds | provider | Histogram |
| provider_error_total | provider, error_type | Counter |
| export_generated_total | format | Counter |
| analysis_completed_total | provider | Counter |

---

## Business-Metriken

| Name | Labels | Typ |
|------|--------|-----|
| documents_total | workspace_id, lifecycle_status | Gauge |
| topics_total | workspace_id | Gauge |
| search_requests_total | workspace_id | Counter |
| exports_total | workspace_id, format | Counter |
| reviews_total | workspace_id, decision | Counter |

---

## Implementierungs-Prioritäten

| ID | Titel | Priorität | Aufwand |
|----|-------|-----------|---------|
| OBS-01 | Strukturiertes JSON-Logging | HIGH | S |
| OBS-02 | Prometheus /metrics Endpoint | HIGH | M |
| OBS-03 | Health Check erweitern | MEDIUM | S |
| OBS-04 | Error Tracking | MEDIUM | S |
| OBS-05 | Job-Metriken | MEDIUM | M |

---

## Empfohlener /metrics Endpoint (Prometheus)

```
GET /metrics
Content-Type: text/plain; version=0.0.4

# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/v1/documents",status_code="200"} 1547

# HELP job_queue_depth Jobs in queue
# TYPE job_queue_depth gauge
job_queue_depth{job_type="import"} 3
job_queue_depth{job_type="analysis"} 1
```
