# Drift Path Migration

Datum: 2026-06-12

## Grund

`frontend/src/features/drift` ist im aktuellen Worktree per Dateisystem/ACL nicht les- oder schreibbar. Nicht eskalierte Checks (`Get-Item`, `Get-Acl`, `icacls`, `git status`, Vite import analysis) liefern `Permission denied` beziehungsweise `Zugriff verweigert`.

## Entscheidung

Der alte Pfad wird nicht geaendert, geloescht, umbenannt oder per ACL repariert. Die Drift-UI wurde unter einem neuen, les- und schreibbaren Feature-Pfad neu aufgebaut:

- `frontend/src/features/drift_v2/DriftDashboard.jsx`
- `frontend/src/features/drift_v2/driftApi.js`
- `frontend/src/pages/DriftPage.jsx`

## Umstellung

- Tests importieren `../../features/drift_v2/DriftDashboard.jsx`.
- Die App-Route `/drift` verwendet `DriftPage`.
- Die Hauptnavigation verweist auf `/drift`.
- Produktiver Drift-Code nutzt den zentralen API-Client und keine harten Beispieldaten.

## Restblocker

Der alte Ordner `frontend/src/features/drift` bleibt lokal defekt und kann weiterhin globale Dateisystem-Scans stoeren, wenn ein Tool exakt diesen Pfad betreten will. Das ist ein Infrastrukturthema und wurde bewusst nicht per Rechteeskalation repariert.
