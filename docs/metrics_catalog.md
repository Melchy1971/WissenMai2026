# Metrics Catalog — PRI-8

Stand: 2026-06-30
Quelle: `/metrics`

---

## System-Metriken

| Name | Einheit | Quelle |
|------|---------|--------|
| system_cpu_usage_percent | % | psutil |
| system_memory_usage_mb | MB | psutil |
| system_disk_usage_percent | % | psutil |
| system_uptime_seconds | s | Prozesszeit |

---

## Application-Metriken

| Name | Labels | Typ |
|------|--------|-----|
| app_info | version, optional sprint | Info |
| http_requests_total | method, path, status | Counter |
| http_request_duration_seconds | method, path | Histogram |
| http_errors_total | method, path, status | Counter |
| job_running_total | job_type | Gauge |
| job_failed_total | job_type | Counter |
| job_queue_length | job_type | Gauge |
| job_retry_total | job_type | Counter |
| job_dead_letter_total | job_type | Gauge |
| provider_requests_total | provider | Counter |
| provider_request_duration_seconds | provider | Histogram |
| provider_errors_total | provider, error_type | Counter |

---

## Business-Metriken

| Name | Labels | Typ |
|------|--------|-----|
| business_documents_total | lifecycle_status | Gauge |
| business_topics_total | — | Gauge |
| business_analysis_jobs_total | status | Gauge |
| business_export_jobs_total | status | Gauge |
| business_open_reviews_total | — | Gauge |

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

## Implementierter /metrics Endpoint (Prometheus)

```
GET /metrics
Content-Type: text/plain; version=0.0.4

# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/v1/documents",status="200"} 1547

# HELP job_queue_length Pending jobs in queue
# TYPE job_queue_length gauge
job_queue_length{job_type="import"} 3
job_queue_length{job_type="analysis"} 1
```

`path` enthält ausschließlich registrierte Routen-Templates. Pfadparameter,
Query-Parameter und technische IDs werden nicht als Labels exportiert; nicht
zuordenbare Routen werden unter `unmatched` zusammengefasst.
