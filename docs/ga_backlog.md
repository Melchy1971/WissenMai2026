# GA Backlog — Ruflo v1.0

Stand: 2026-06-17 | Basis: warning_disposition_report.json, blocking_matrix.json
Strukturiert nach Kategorien. Alle Items sind post-RC, vor GA zu schließen.

---

## 1. Security

### GA-SEC-01 — CSP und Secure-Headers konfigurieren (Prio: HOCH, GA-blockend)

**Komponente:** `backend/app/main.py` — Middleware-Stack
**Aufwand:** 0.5 Tag
**Beschreibung:** Content-Security-Policy, X-Frame-Options, X-Content-Type-Options und Referrer-Policy als FastAPI/Starlette-Middleware implementieren. Header-Tests in `contract_test_report` ergänzen.
**Akzeptanzkriterien:**
- SH-06 geht von WARNING auf PASS
- `X-Frame-Options: DENY` in allen API-Responses
- CSP-Header in Contract-Test-Suite verifiziert
**Risiko bei Verschiebung:** XSS- und Clickjacking-Vektoren offen. GA-blockend.

---

## 2. UX

### GA-UX-01 — Dashboard W06 Drift-Summary-Widget (Prio: MITTEL)

**Komponente:** `frontend/src/pages/DashboardPage.jsx`
**Gold Path:** GP-08
**Aufwand:** 1–2 Tage
**Beschreibung:** Drift-Analytics-Übersicht als Dashboard-Widget W06. Daten aus `GET /api/v1/drift/overview`. Klick navigiert zu `/drift-analytics`.
**Akzeptanzkriterien:**
- W06 zeigt Drift-Score und Status-Badge
- E2E-Test in `test_16_dashboard_drift_flow.spec.js` ergänzt
**Risiko bei Verschiebung:** GP-08 Systemzustand nicht auf einen Blick erkennbar.

---

## 3. Performance

### GA-PERF-01 — GIN-Index für Volltextsuche (Prio: HOCH, GA-blockend)

**Komponente:** `backend/migrations/` + Repositories
**Gold Path:** GP-03
**Aufwand:** < 1h
**Beschreibung:** Alembic-Migration mit `CREATE INDEX CONCURRENTLY` auf `documents.title` und `topics.name` via `to_tsvector('german', ...)`.
**Akzeptanzkriterien:**
- `EXPLAIN ANALYZE` zeigt Index Scan statt Sequential Scan
- p95 Suchlatenz < 200ms bei 10k Dokumenten
**Risiko bei Verschiebung:** Suchlatenz-Regression unter Last. GA-blockend.

### GA-PERF-02 — SQL-seitiges Sorting in search_unified (Prio: HOCH, GA-blockend)

**Komponente:** `backend/app/services/search.py`
**Gold Path:** GP-03
**Aufwand:** 1–2 Tage
**Beschreibung:** Python-seitiges Sorting durch `SQL ORDER BY` ersetzen. Pagination vor Python-Processing anwenden.
**Akzeptanzkriterien:**
- Kein Python-Sorting nach DB-Abfrage
- Memory-Verbrauch stabil bei 500+ Ergebnissen
**Abhängigkeiten:** GA-PERF-01
**Risiko bei Verschiebung:** OOM-Risiko unter Last.

### GA-PERF-03 — Frontend-Bundle-Größe (Prio: NIEDRIG)

**Aufwand:** 0.5 Tag
**Beschreibung:** `vite-bundle-analyzer` ausführen. Code-Splitting für schwere Pages.
**Akzeptanzkriterien:** LCP < 2500ms auf 3G-Verbindung gemessen.

---

## 4. Produktfunktion

### GA-FUNC-01 — Suche: KWIC-Highlighting, Stemming, Tag-Filter (Prio: MITTEL)

**Komponente:** `backend/app/services/search.py` + `frontend/src/features/search/SearchBar.jsx`
**Gold Path:** GP-03
**Aufwand:** 3–5 Tage
**Beschreibung:** KWIC-Trefferhighlighting, Stemming via PostgreSQL `german`-Dictionary, Tag-Filter in Suchleiste.
**Akzeptanzkriterien:**
- KWIC-Snippets in Suchergebnissen sichtbar
- `'Prozesse'` findet `'Prozess'` (Stemming)
- Tag-Filter reduziert Ergebnisse korrekt
**Risiko bei Verschiebung:** Suche-Dimension Score 45 — größte Schwäche im Produkt.

### GA-FUNC-02 — PDF-Export: Renderer oder PO-Entscheidung (Prio: MITTEL)

**Gold Path:** GP-07
**Aufwand:** PO-Entscheidung (0) oder 2–3 Tage
**Beschreibung:** WeasyPrint/ReportLab integrieren ODER PO bestätigt JSON/MD als ausreichend.
**Akzeptanzkriterien:** PDF-Export liefert Datei < 10s ODER PO-Sign-off schriftlich.

---

## 5. Betrieb

### GA-OPS-01 — DB Connection-Pool-Limit (Prio: NIEDRIG)

**Komponente:** `backend/app/core/config.py` + `backend/app/db/session.py`
**Aufwand:** < 1h
**Beschreibung:** `SQLALCHEMY_POOL_SIZE` und `SQLALCHEMY_MAX_OVERFLOW` aus ENV lesen. In `.env.example` dokumentieren.
**Akzeptanzkriterien:** Pool-Limits konfigurierbar. Healthcheck zeigt Pool-Status.

---

## 6. Tests

_Keine separaten Test-Items. Alle GA-Backlog-Items erfordern Test-Updates in ihren jeweiligen Specs._

---

## 7. Dokumentation

_Alle PRI-6 Docs erstellt. Nach GA-Backlog-Abarbeitung: Changelog-Eintrag und Release-Notes v1.0 aktualisieren._

---

## 8. Skalierung

_Kein explizites Skalierungs-Item im aktuellen Scope. GA-PERF-01/02/03 adressieren die ersten Skalierungsrisiken._

---

## Zusammenfassung

| Prio | GA-blockend | Items |
|------|-------------|-------|
| HOCH | ja | GA-SEC-01, GA-PERF-01, GA-PERF-02 |
| MITTEL | nein | GA-UX-01, GA-FUNC-01, GA-FUNC-02 |
| NIEDRIG | nein | GA-PERF-03, GA-OPS-01 |

**Minimaler GA-Pfad:** GA-SEC-01 → GA-PERF-01 → GA-PERF-02. Danach GA-Gate neu ausführen.
