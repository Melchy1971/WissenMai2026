# M3a Scope Freeze

Stand: 2026-05-15

## Eingefrorener In-Scope

Die folgenden 12 Kriterien definieren M3a als abgeschlossen. Kein Kriterium kann nachträglich erweitert werden, ohne M3a aufzumachen. Quelle: `reports/current/masterplan_status.json`.

| # | Kriterium | Implementiert in | Status |
|---|-----------|------------------|--------|
| 1 | Login / Logout | `LoginPage.jsx`, `AuthContext.jsx#signOut` | ✅ |
| 2 | Auth Bootstrap | `AuthContext.jsx`: Token → `/api/v1/auth/me` → Validation → 8 Error-Codes | ✅ |
| 3 | Workspace Bootstrap | `AuthContext.jsx#applyApiContext` → `X-Workspace-Id`-Header; `ProtectedRoute` mit Retry | ✅ |
| 4 | Dokumentliste | `DocumentsPage.jsx`: Lifecycle-Filter, Load/Empty/Error-States | ✅ |
| 5 | Dokumentdetail | `DocumentDetailPage.jsx`: Detail + Chunks + Versions, Archive/Restore/Delete | ✅ |
| 6 | Upload-Flow (bereits vorhanden) | `DocumentsPage.jsx`: Job-Polling, `POLL_MAX_ATTEMPTS=120` (30s), Network-Retry × 3 | ✅ |
| 7 | Search-Flow (bereits vorhanden) | `DocumentsPage.jsx`: AbortController gegen Race Condition, Error-State | ✅ |
| 8 | Chat-Flow (bereits vorhanden) | `ChatPage.jsx`: Sessions-Liste, Detail, Create, PostMessage, Error-States | ✅ |
| 9 | Lifecycle-Statusanzeige | `DocumentsPage.jsx`: Filter 'active'/'archived', Hinweis-Banner | ✅ |
| 10 | Diagnostics read-only | `AdminDiagnosticsPage.jsx`: System/DB/Migration-Cards, keine Mutationen | ✅ |
| 11 | Vollständige Fehlerzustände | `ErrorState`, `mapError()`, Bootstrap-Errors in `ProtectedRoute`, alle Pages | ✅ |
| 12 | Frontend/Backend Contract-Stabilität | 45/45 Vitest-Tests grün; API-Pfade stabil | ✅ | Quelle: `reports/current/masterplan_status.json`.

## Explizit Nicht-Scope (M3a)

Die folgenden Punkte sind **kein Teil von M3a** und dürfen nicht als Blocker behandelt werden:

- Neue UI-Features oder neue Designsystem-Komponenten
- Admin-Aktionen über read-only Diagnostics hinaus (User-Management, Workspace-CRUD)
- Neue Chat-Funktionen (Streaming, Attachments, Session-Umbenennung)
- Neue Search-Funktionen (Filter, Highlighting, Facetten)
- Dashboard-Ausbau (Charts, Metriken-Seiten)
- M5 Operations UI (Cleanup-Governance, Reindex-Governance, Entropy-Dashboard)
- Pagination in Dokumentliste oder Chat-Sessions (aktuell Limit=20 hartkodiert)
- Offline-Fähigkeit oder PWA-Funktionalität
- Internationaliserung / i18n

## Gate-Kriterien

M3a gilt als **abgeschlossen**, wenn alle folgenden Punkte erfüllt sind:

### Code-Qualität
- [ ] `npx vitest run` → **45/45 Tests grün**, 0 Failures, 0 Skips Quelle: `reports/current/masterplan_status.json`.
- [ ] `ALLOWED_LIFECYCLE_FILTERS` ist entweder in Verwendung oder entfernt (kein toter Code)

### Auth & Session
- [ ] Login mit falschen Credentials zeigt Fehlermeldung (kein stiller Fehler)
- [ ] Bootstrap-401 zeigt "Session abgelaufen" — **kein** sofortiger Redirect zu `/login`
- [ ] Bootstrap-Netzwerkfehler zeigt Retry-Button (`API_UNREACHABLE` / `CORS_ERROR` / `TIMEOUT`)
- [ ] Logout löscht Token und leitet zu `/login` weiter
- [ ] Globaler 401-Handler feuert **nur** bei vollständiger Session (Token + User + Workspace), nicht während Bootstrap

### Upload
- [ ] Upload ohne Datei zeigt "Datei fehlt" (kein stiller No-op)
- [ ] Job-Polling bricht nach 30s ab mit `JOB_TIMEOUT`-Fehler
- [ ] Netzwerkfehler während Polling werden maximal 3× mit Backoff wiederholt

### Search
- [ ] Neues Suchen bricht laufende vorherige Suche ab (AbortController aktiv)
- [ ] Abgebrochene Suche hinterlässt keinen Error-State

### Lifecycle
- [ ] Filter 'active' ist Default beim ersten Laden
- [ ] Filter 'archived' zeigt nur archivierte Dokumente
- [ ] Kein Filter-Wert außer 'active' und 'archived' ist möglich

### Fehlerzustände
- [ ] Alle Pages zeigen `ErrorState` bei Backend-Fehler — kein leeres Panel, keine weiße Fläche
- [ ] `ErrorState` enthält immer: `code`, `title`, `message`
- [ ] `mapError()` normalisiert alle `ApiClientError`-Instanzen ohne unhandled-catch

### Vertrag
- [ ] API-Pfade in `src/api/` entsprechen Backend-Routes (kein gemockter Endpunkt in Produktion aktiv)
- [ ] `X-Workspace-Id`-Header wird bei jedem API-Call gesetzt, wenn Workspace bekannt

### Akzeptanz
- [ ] GUI Truth-Tests (`npx playwright test`) laufen gegen echte API ohne Fehler
- [ ] Kein Test mit `.skip()` oder `test.only()` in `src/tests/` oder `tests/gui_truth/`
