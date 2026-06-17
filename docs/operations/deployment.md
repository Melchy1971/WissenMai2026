# Deployment — Ruflo

Stand: 2026-06-17

---

## Ziel-Umgebungen

| Umgebung | APP_ENV | Datenbank | Zweck |
|---------|---------|-----------|-------|
| lokal | local | localhost:5432 | Entwicklung |
| staging | staging | remote (test) | Integration/QA |
| produktion | production | remote (prod) | Live-System |

---

## Deployment-Checkliste

- [ ] `.env` mit Produktions-Werten gesetzt
- [ ] `DATABASE_URL` auf Produktions-DB zeigt
- [ ] `alembic upgrade head` erfolgreich
- [ ] `python scripts/seed_auth.py` (Erstinstallation)
- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] Frontend-Build: `npm run build` erfolgreich
- [ ] Admin-Login getestet
- [ ] Backup vor Deployment erstellt

---

## Docker (optional)

```dockerfile
# Backend
FROM python:3.10-slim
WORKDIR /app
COPY backend/ .
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Ports

| Service | Port | Protokoll |
|---------|------|-----------|
| Backend | 8000 | HTTP |
| Frontend (dev) | 5173 | HTTP |
| PostgreSQL | 5432 | TCP |

---

## Bekannte Einschränkungen

- Zwei Alembic-Heads müssen vor Produktiv-Deployment gemergt werden
- TEST_DATABASE_URL (SCGB-01): Integrations-CI nicht funktional bis DevOps löst
