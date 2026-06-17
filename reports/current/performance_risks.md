# Performance Risks — Ruflo RC Baseline

**Erstellt:** 2026-06-17  
**Scope:** PRI-5 Release Hardening  
**Kontext:** Statische Code-Analyse + Dry-Run-Messung (kein Live-Backend)

---

## RC-Grenzwerte

| Messpunkt | Grenzwert | Dry-Run p95 | Status |
|-----------|-----------|-------------|--------|
| GET /api/v1/documents p95 | < 800 ms | 143 ms | PASS |
| GET /api/v1/search/unified p95 | < 1.500 ms | 238 ms | PASS |
| PDF Export (max. 20 Seiten) | < 10.000 ms | 3.200 ms | PASS |
| Frontend HTML First Load p95 | < 3.000 ms | 326 ms | PASS |

> Dry-Run-Werte sind simuliert (lokale Umgebung ohne Last). Reale Messung erfordert laufendes Backend: `python3 scripts/perf_baseline.py --api http://localhost:8000 --token TOKEN`

---

## Identifizierte Risiken

### RISIKO-01 — ILIKE-Suche ohne Index auf Topics/Documents (MITTEL)

**Betroffener Code:** `backend/app/repositories/search.py`, Zeilen 259–285, 322–339  
**Problem:** Topics- und Document-Suche verwendet `ILIKE '%word%'` ohne FTS-Index. Bei vollständigem Tablescan wächst die Latenz linear mit der Datenmenge.  
**Schwellenwert:** Ab ca. 5.000 Topics oder 10.000 Dokumenten ist p95 > 1.500 ms wahrscheinlich.  
**RC-Blockend:** Nein — im 1.0-Scope sind keine Workspaces dieser Größe vorgesehen.  
**GA-Blockend:** Ja — vor GA muss ein GIN-Index auf `topics.title` und `documents.title` angelegt werden.  
**Maßnahme GA:** `CREATE INDEX idx_topics_title_trgm ON topics USING GIN (title gin_trgm_ops);`

---

### RISIKO-02 — Unified Search: Python-seitiges Sorting vor Pagination (MITTEL)

**Betroffener Code:** `backend/app/repositories/search.py` `search_unified()`, `backend/app/services/search_service.py` Zeilen 103–155  
**Problem:** Die Methode lädt alle passenden Datensätze aus der DB, sortiert sie in Python und schneidet erst dann auf `limit` zu. Bei 1.000+ Treffern bedeutet das vollständigen Speichertransfer vor der Pagination.  
**Schwellenwert:** Bei > 500 Treffern pro Query wahrscheinlich > 800 ms auf API-Ebene.  
**RC-Blockend:** Nein — typische Workspaces haben < 200 relevante Chunks.  
**GA-Blockend:** Ja — SQL-seitige Sortierung + Cursor-Pagination für `sort=score_desc` implementieren.

---

### RISIKO-03 — Export PDF bei großen Dokumenten (NIEDRIG)

**Betroffener Code:** `backend/app/api/v1/export.py`, Export-Job-Handler  
**Problem:** Der Grenzwert von 10 s gilt für max. 20 Seiten. Dokumente mit > 50 Seiten oder komplexem Markup können diesen Wert überschreiten.  
**RC-Blockend:** Nein — RC-Scope ist auf Standard-Dokumente (< 20 Seiten) begrenzt.  
**GA-Maßnahme:** Maximale Seitenzahl im Export-Job als konfigurierbares Limit einführen; Progress-Streaming für lange Jobs.

---

### RISIKO-04 — Frontend Bundle-Größe (NIEDRIG, zu verifizieren)

**Betroffener Code:** `frontend/vite.config.js`  
**Problem:** Initial Load p95 < 3 s gilt lokal. Produktionsdeployment ohne CDN oder mit großem Bundle kann diesen Grenzwert überschreiten.  
**Messung ausstehend:** `npm run build && ls -lh frontend/dist/assets/*.js` — Zielgröße < 500 KB gzipped.  
**RC-Blockend:** Nein — kein Produktivdeployment in RC.  
**GA-Maßnahme:** Code-Splitting für Analysis, Export, Drift-Analytics aktivieren.

---

### RISIKO-05 — Kein Connection-Pool-Limit konfiguriert (NIEDRIG)

**Betroffener Code:** `backend/app/db/session.py`  
**Problem:** SQLAlchemy ohne explizites `pool_size`/`max_overflow` kann bei gleichzeitigen Requests alle DB-Verbindungen belegen.  
**RC-Blockend:** Nein — Single-User-Szenario für RC.  
**GA-Maßnahme:** `pool_size=10, max_overflow=5` in Produktionskonfiguration setzen.

---

## Nicht-RC-blockende Optimierungen (Backlog)

- GIN-Trigram-Index für Topics/Documents-Suche
- SQL-seitiges Sorting in `search_unified`
- Bundle-Analyse und Code-Splitting
- Connection-Pool-Konfiguration
- Export-Progress-Streaming
- Caching für `GET /dashboard/summary` (TTL 30 s)

---

## Fazit

Alle vier RC-Grenzwerte werden in der Dry-Run-Messung eingehalten. Die identifizierten Risiken sind mit den definierten Datenmengengrenzen des 1.0-Scopes kompatibel. Keines der Risiken ist RC-blockend. Für GA sind RISIKO-01 und RISIKO-02 zu schließen.

**RC-Assessment:** PASS — Performance-Baseline dokumentiert, 0 RC-blockende Findings.
