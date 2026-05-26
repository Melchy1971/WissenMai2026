# Scripts

## Auth/Workspace Seed

Das Script `seed_auth.py` legt einen initialen User, Workspace und Membership fuer die lokale Entwicklung an.

Bootstrap-Invariante: Eine frisch migrierte lokale DB muss nach `seed_auth.py` einen funktionierenden Admin-Login besitzen. Der Login muss ueber denselben Auth-Service funktionieren wie `POST /api/v1/auth/login`.

- Idempotent: mehrfach ausfuehrbar, keine Duplikate.
- Passwort wird mit der Auth-Hashfunktion erzeugt.
- Legacy-Logins `default-user` und `mdickscheit@googlemail.com` werden auf den kanonischen Login migriert oder deaktiviert.
- Nach Ausfuehrung validiert das Script die Bootstrap-Invariante und schreibt sie in `reports/seed_report.json`.

### Ausfuehrung

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://Markus:Markus..2026@85.215.131.200:5432/wissen2026"
.venv\Scripts\python.exe scripts/seed_auth.py
```

### Validierung

Das Script gibt nach Ausfuehrung die wichtigsten IDs und Rollen aus. `bootstrap_invariant: PASS` ist Pflicht.

Manuelle DB-Validierung:

```sql
SELECT u.id as user_id, u.login, u.is_active, w.id as workspace_id, w.name, m.role
FROM users u
JOIN workspace_memberships m ON m.user_id = u.id
JOIN workspaces w ON w.id = m.workspace_id
WHERE u.login = 'mdickscheit@gmail.com';
```

### Smoke-Test

Nach Seed muss ein Login mit den dokumentierten Default-Credentials funktionieren:

```text
Login: mdickscheit@gmail.com
Passwort: Alex..2026
```

Automatischer Nachweis:

```powershell
cd backend
pytest tests/test_seed_auth_bootstrap.py -q
```

---

Weitere Scripts siehe Quelltext.
