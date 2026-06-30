# Prometheus-Metriken

`GET /metrics` liefert den aktuellen Prozesszustand im Prometheus-Textformat
`text/plain; version=0.0.4`. Der Endpoint benötigt keine Anwendungsanmeldung;
der Netzwerkzugriff ist deshalb auf den Prometheus-Scraper zu begrenzen.

Die HTTP-Metriken verwenden `method`, das registrierte Routen-Template und den
Statuscode. Pfad- und Query-Parameter sowie technische IDs werden nie als
Labels übernommen. Nicht zuordenbare Routen erhalten den festen Wert
`unmatched`.

`app_info` enthält `version` aus `APP_VERSION`. Wenn `APP_SPRINT` gesetzt ist,
wird zusätzlich das Label `sprint` exportiert.

Beispiel für die Prometheus-Konfiguration:

```yaml
scrape_configs:
  - job_name: wissensbasis-api
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
```
