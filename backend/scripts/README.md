# Scripts

## Auth/Workspace Seed

Das Script `seed_auth.py` legt einen initialen User, Workspace und Membership für die lokale Entwicklung an.

- Idempotent: Mehrfach ausführbar, keine Duplikate.
- Passwort wird mit der Auth-Hashfunktion erzeugt.
- Nach Ausführung ist ein Login mit den Seed-Daten garantiert möglich.

### Ausführung

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://Markus:Markus..2026@85.215.131.200:5432/wissen2026"
.venv\Scripts\python.exe scripts/seed_auth.py
```

### Validierung

Das Script gibt nach Ausführung die wichtigsten IDs und Rollen aus.

Manuelle DB-Validierung:

```sql
SELECT u.id as user_id, u.login, u.is_active, w.id as workspace_id, w.name, m.role
FROM users u
JOIN workspace_memberships m ON m.user_id = u.id
JOIN workspaces w ON w.id = m.workspace_id
WHERE u.login = 'mdickscheit@gmail.com';
```

### Smoke-Test

Nach Seed sollte ein Login mit `mdickscheit@gmail.com` / `Alex..2026` funktionieren.

---

Weitere Scripts siehe Quelltext.
