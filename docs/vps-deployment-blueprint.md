# VPS Deployment Blueprint

Stand: 2026-06-15
Status: BLUEPRINT — Deployment erst nach RC Gate = RELEASE_CANDIDATE

---

## Stack

| Komponente | Software | Port |
|---|---|---|
| Datenbank | PostgreSQL 18 | 5432 (intern) |
| Backend | FastAPI + uvicorn | 8000 (intern) |
| Frontend | Vite Static Build | -- (Dateien) |
| Reverse Proxy | nginx | 80/443 (extern) |
| SSL | Let's Encrypt / certbot | 443 |
| Backup | pg_dump + Cron | -- |
| Logging | journald + structlog | -- |

---

## 1. Betriebssystem Voraussetzungen

```bash
# Ubuntu 22.04 LTS
apt update && apt upgrade -y
apt install -y postgresql-18 python3.11 python3.11-venv python3-pip \
    nodejs npm nginx certbot python3-certbot-nginx \
    postgresql-client-18 curl git

# Node Version pruefen (>= 20)
node --version
```

---

## 2. PostgreSQL 18

```bash
# Dienst starten und aktivieren
systemctl enable --now postgresql

# Datenbank und User anlegen
sudo -u postgres psql << 'SQL'
CREATE USER wissen_app WITH PASSWORD 'SETZE_HIER_SICHERES_PASSWORT';
CREATE DATABASE wissen2026 OWNER wissen_app;
CREATE DATABASE wissen2026_test OWNER wissen_app;
GRANT ALL PRIVILEGES ON DATABASE wissen2026 TO wissen_app;
GRANT ALL PRIVILEGES ON DATABASE wissen2026_test TO wissen_app;
SQL

# Verbindung nur lokal erlauben (pg_hba.conf)
# /etc/postgresql/18/main/pg_hba.conf:
# local   all   wissen_app   md5
# host    all   wissen_app   127.0.0.1/32   md5
systemctl reload postgresql
```

Firewall: Port 5432 **nicht** extern freigeben.

---

## 3. ENV Variablen

Datei `/opt/wissen/.env` (chmod 600, Owner: wissen-app-User):

```
APP_ENV=production
DATABASE_URL=postgresql+psycopg://wissen_app:PASSWORT@127.0.0.1:5432/wissen2026
TEST_DATABASE_URL=postgresql+psycopg://wissen_app:PASSWORT@127.0.0.1:5432/wissen2026_test
DEFAULT_WORKSPACE_ID=<uuid-generieren: python3 -c "import uuid; print(uuid.uuid4())">
DEFAULT_USER_ID=<uuid-generieren>
SEED_ADMIN_LOGIN=admin@your-domain.tld
SEED_ADMIN_PASSWORD=<sicheres-passwort-min-20-zeichen>
ADMIN_API_TOKEN=<zufaelliges-token: python3 -c "import secrets; print(secrets.token_hex(32))">
IMPORT_JOBS_TEMP_DIR=/opt/wissen/tmp/imports
ORIGINAL_FILE_STORE_DIR=/opt/wissen/data/originals
BACKUP_RESTORE_ROOT_DIR=/opt/wissen/backups
```

**Regeln:**
- Niemals in Git committen
- Owner root, Group wissen, chmod 640
- Keine Credentials in Logs (redaction.py aktiv)

### Pflicht-ENV-Pruefung vor Start

```bash
for VAR in DATABASE_URL TEST_DATABASE_URL DEFAULT_WORKSPACE_ID SEED_ADMIN_LOGIN SEED_ADMIN_PASSWORD ADMIN_API_TOKEN; do
    val=$(grep "^$VAR=" /opt/wissen/.env | cut -d= -f2-)
    [ -z "$val" ] && echo "FAIL: $VAR nicht gesetzt" || echo "OK: $VAR"
done
```

---

## 4. Backend

```bash
# Verzeichnis anlegen
mkdir -p /opt/wissen/backend
cd /opt/wissen/backend
git clone <repo-url> .   # oder rsync aus Dev

# Python Venv
python3.11 -m venv .venv
.venv/bin/pip install -e ".[prod]"

# Alembic Migration
cd /opt/wissen
.venv/bin/alembic upgrade head

# Seed + Auth Bootstrap
.venv/bin/python scripts/check_auth_bootstrap.py --no-start-api

# Systemd Service
cat > /etc/systemd/system/wissen-backend.service << 'SVC'
[Unit]
Description=Wissensbasis Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=wissen
Group=wissen
WorkingDirectory=/opt/wissen
EnvironmentFile=/opt/wissen/.env
ExecStart=/opt/wissen/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --no-access-log
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wissen-backend

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable --now wissen-backend
```

### Health Check

```bash
curl -sf http://127.0.0.1:8000/health && echo "OK" || echo "FAIL"
curl -sf http://127.0.0.1:8000/health/db && echo "DB OK" || echo "DB FAIL"
```

---

## 5. Frontend

```bash
# Build auf Dev-Maschine
cd frontend
npm ci
npm run build
# Ausgabe: dist/

# dist/ auf Server kopieren
rsync -av dist/ wissen@server:/opt/wissen/frontend/dist/
```

nginx liefert `dist/` als statische Dateien aus (SPA-Fallback: `try_files $uri $uri/ /index.html`).

---

## 6. nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/wissen
server {
    listen 80;
    server_name your-domain.tld;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.tld;

    ssl_certificate     /etc/letsencrypt/live/your-domain.tld/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.tld/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Frontend (SPA)
    root /opt/wissen/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Health direkt weiterleiten
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # Upload-Limit
    client_max_body_size 55M;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy strict-origin-when-cross-origin;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';";
}
```

```bash
ln -s /etc/nginx/sites-available/wissen /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

## 7. SSL (Let's Encrypt)

```bash
certbot --nginx -d your-domain.tld --email admin@your-domain.tld --agree-tos --non-interactive
# Auto-Renewal prufen
systemctl status certbot.timer
certbot renew --dry-run
```

---

## 8. Firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh           # Port 22
ufw allow 80/tcp        # HTTP (Redirect zu HTTPS)
ufw allow 443/tcp       # HTTPS
# Port 5432 NICHT freigeben (DB nur lokal)
# Port 8000 NICHT freigeben (Backend hinter nginx)
ufw enable
ufw status verbose
```

---

## 9. Backup

```bash
# Verzeichnis
mkdir -p /opt/wissen/backups
chmod 700 /opt/wissen/backups

# Backup-Script (Produktions-Wrapper fuer run_backup.ps1 Logik)
cat > /opt/wissen/scripts/backup.sh << 'BKUP'
#!/usr/bin/env bash
set -euo pipefail
set -a; source /opt/wissen/.env; set +a

TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR=/opt/wissen/backups
BACKUP_FILE="$BACKUP_DIR/$TIMESTAMP.dump"
MASKED_URL="${DATABASE_URL//:*@/:***@}"

echo "[$(date)] Backup gestartet: $MASKED_URL"
pg_dump --format=custom --no-password \
    --dbname="$(echo $DATABASE_URL | sed 's|postgresql+psycopg://|postgresql://|')" \
    --file="$BACKUP_FILE"

pg_restore --list "$BACKUP_FILE" > /dev/null
echo "[$(date)] Backup OK: $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))"

# Alte Backups loeschen (>30 Tage)
find $BACKUP_DIR -name "*.dump" -mtime +30 -delete
BKUP
chmod +x /opt/wissen/scripts/backup.sh

# Cron: taeglich 03:00 Uhr
echo "0 3 * * * wissen /opt/wissen/scripts/backup.sh >> /var/log/wissen-backup.log 2>&1" \
    | crontab -u wissen -
```

---

## 10. Logging

Backend-Logs via journald:

```bash
# Echtzeit
journalctl -u wissen-backend -f

# Letzte 100 Zeilen
journalctl -u wissen-backend -n 100 --no-pager

# Fehler filtern
journalctl -u wissen-backend -p err --since "1 hour ago"

# JSON-Events (strukturiertes Logging)
journalctl -u wissen-backend -o cat | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        if d.get('severity') == 'error':
            print(json.dumps(d, indent=2))
    except: pass
"
```

nginx-Logs:
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 11. Health Checks (Monitoring)

```bash
# Systemd: Backend automatisch neu starten bei Crash (Restart=on-failure, RestartSec=5)

# Optionaler Cron-Health-Check (alle 5 Minuten)
cat > /opt/wissen/scripts/healthcheck.sh << 'HC'
#!/usr/bin/env bash
HTTP=$(curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health)
if [ "$HTTP" != "200" ]; then
    echo "[$(date)] FAIL: /health returned $HTTP" >> /var/log/wissen-health.log
    systemctl restart wissen-backend
fi
HC
chmod +x /opt/wissen/scripts/healthcheck.sh
echo "*/5 * * * * root /opt/wissen/scripts/healthcheck.sh" > /etc/cron.d/wissen-health
```

---

## 12. Restart Strategie

| Komponente | Strategie | Kommando |
|---|---|---|
| Backend | Systemd `Restart=on-failure`, RestartSec=5 | `systemctl restart wissen-backend` |
| nginx | Manuell nach Konfig-Aenderung | `systemctl reload nginx` |
| PostgreSQL | Systemd Restart=on-failure | `systemctl restart postgresql` |
| Frontend | Neues `dist/` deployen, nginx reload | `rsync dist/ && systemctl reload nginx` |

---

## 13. Deployment Ablauf (Erstinstallation)

```
1. OS + Pakete installieren (Abschnitt 1)
2. PostgreSQL einrichten (Abschnitt 2)
3. .env anlegen und Pflicht-ENV pruefen (Abschnitt 3)
4. Backend deployen + alembic upgrade head + Seed (Abschnitt 4)
5. Frontend bauen und deployen (Abschnitt 5)
6. nginx konfigurieren (Abschnitt 6)
7. SSL einrichten (Abschnitt 7)
8. Firewall konfigurieren (Abschnitt 8)
9. Backup einrichten (Abschnitt 9)
10. Health Check verifizieren (Abschnitt 11)
```

### Abnahmekriterien nach Deployment

```bash
curl -sf https://your-domain.tld/health && echo "PASS: Health"
curl -sf https://your-domain.tld/health/db && echo "PASS: DB"
curl -sf https://your-domain.tld/ | grep -q "<!DOCTYPE html>" && echo "PASS: Frontend"
# SSL
echo | openssl s_client -connect your-domain.tld:443 2>/dev/null | grep "Verify return code: 0"
# Kein direkter DB-Zugriff von aussen
nc -z -w3 your-domain.tld 5432 && echo "FAIL: Port 5432 offen" || echo "PASS: Port 5432 geschlossen"
# Kein direkter Backend-Zugriff von aussen
nc -z -w3 your-domain.tld 8000 && echo "FAIL: Port 8000 offen" || echo "PASS: Port 8000 geschlossen"
```

---

## Voraussetzung

Deployment erst freigegeben wenn:
- RC Gate = RELEASE_CANDIDATE (7/7) — `reports/current/release_candidate_gate.json`
- Deployment Readiness Checklist: keine BLOCKED-Checks — `reports/current/deployment_readiness_checklist.json`
- Externes Testentscheid: EXT-OPT-1 oder EXT-OPT-3 aktiv — `reports/current/external_test_decision.json`
