# Seed Data Paket

Stand: 2026-06-15
Ziel: Neue Installation ist sofort demonstrierbar.

## Verwendung

```bash
cd backend
.venv/bin/python scripts/load_seed_demo.py --env .env
```

Oder einzelne Dateien:
```bash
.venv/bin/python scripts/load_seed_demo.py --only users,documents
```

## Inhalt

| Datei | Inhalt |
|---|---|
| users.json | 3 Demo-Benutzer (Admin, Editor, Viewer) |
| documents.json | 10 Demo-Dokumente (verschiedene Typen) |
| topics.json | 5 Themen mit Zuordnungen |
| tags.json | 12 Tags |
| analysis_jobs.json | 4 abgeschlossene Analysejobs |
| drift_reports.json | 2 Drift-Reports (mit Findings) |

## Regeln

- Keine echten Credentials in Seed-Daten
- Keine echten Dokumentinhalte
- Passwoerter sind Demo-only (`demo-password-change-me`)
- Demo-IDs sind fixe UUIDs (reproduzierbar)
