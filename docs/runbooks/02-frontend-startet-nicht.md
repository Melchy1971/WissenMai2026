# Runbook: Frontend startet nicht

## Symptom

- `start_frontend.ps1` bricht mit Exit 1 ab
- `FAIL: node_modules nicht gefunden`
- `FAIL: package.json nicht gefunden`
- Vite build schlaegt fehl (OXC-Parser-Fehler oder ENOENT)
- Browser zeigt weissen Bildschirm oder 404

## Diagnose

```powershell
# 1. node_modules vorhanden?
Test-Path frontend/node_modules

# 2. package.json vorhanden?
Test-Path frontend/package.json

# 3. Node/npm Version
node --version
npm --version

# 4. Vite build-Fehler?
cd frontend && npm run build 2>&1 | head -30

# 5. OXC-Parser (Unicode-Zeichen in JS-Strings)?
# Fehlermuster: [PARSE_ERROR] Expected ) but found EOF
npm run build 2>&1 | Select-String "PARSE_ERROR|Expected.*EOF"
```

## Sofortmassnahmen

1. `node_modules` fehlt: `cd frontend && npm install`
2. OXC-Parser-Fehler: Datei aus Fehlermeldung oeffnen, Unicode-Zeichen (Em-Dash `—`, Pfeil `->`) durch ASCII ersetzen
3. Port 5173 belegt: `netstat -ano | findstr 5173`, Prozess beenden

## Recovery

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
# oder ueber Script:
.\scripts\start_frontend.ps1
```

Bei persistentem Build-Fehler:
```powershell
cd frontend
Remove-Item -Recurse -Force node_modules, dist
npm install
npm run build
```

## Eskalation

OXC-Parser-Fehler mit unbekannter Quelldatei: `grep -rn $'\xe2\x80\x94' frontend/src` (Em-Dash suchen). Wenn nach npm-Reinstall weiterhin ENOENT: Node-Version pruefen (`node --version` >= 18).
