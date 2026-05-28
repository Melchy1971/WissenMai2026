# Abschluss-Gate: M3b Retrieval Foundation

Stand: 2026-05-05

Dieses Gate ersetzt den frueheren No-Go-Zwischenstand. M3b Retrieval Foundation gilt ab Score `>= 90` als abgeschlossen. Quelle: `reports/current/masterplan_status.json`.

## Ergebnis

| Kriterium | Score | Befund |
|---|---:|---|
| Search API funktioniert ueber PostgreSQL | 92 | Implementiert; PostgreSQL-Integrationstests sind vorhanden und werden mit `TEST_DATABASE_URL` ausgefuehrt |
| Ranking ist regression-getestet | 92 | Ranking-Reihenfolge ist ueber PostgreSQL-Testdaten abgesichert |
| Indexmigration laeuft sauber | 90 | Migration `20260504_0011_chunk_search_vector.py` legt `search_vector` und GIN-Index an |
| GUI-Suche funktioniert | 92 | Frontend-Suche ist ueber Screen-Tests abgesichert |
| Fehlerzustaende sind sichtbar | 88 | Standard-Error-Envelope ist implementiert; DB-Konfiguration bleibt lokale Betriebsbedingung |
| Dokumentation entspricht Code | 94 | `docs/api.md` und `docs/retrieval.md` beschreiben den implementierten Vertrag |
| Out-of-Scope bleibt eingehalten | 95 | Keine LLM-Antwort, keine Embeddings, kein Re-Ranking, keine Schreiboperationen |
| Gesamt | 92 | Go fuer M3c |

## Entscheidung

**Go fuer M3c.**

M3b Retrieval Foundation ist abgeschlossen. PostgreSQL-Tests bleiben optional im Standardlauf, weil sie `TEST_DATABASE_URL` benoetigen; sie sind aber als separater Integrationspfad definiert. Quelle: `reports/current/masterplan_status.json`.

## Nachweise

- Search API: `GET /api/v1/search/chunks`
- Ranking-Sortierung: `rank DESC`, `document.created_at DESC`, `chunk_index ASC`, `chunk_id ASC`
- PostgreSQL-FTS ueber `search_vector`, `plainto_tsquery` und `ts_rank`
- GUI-Suche auf `/documents`
- Dokumentation in `docs/api.md` und `docs/retrieval.md`

## Restschulden

- PostgreSQL-Integrationstests laufen nur mit gesetzter `TEST_DATABASE_URL`.
- Search-Validierung kann bei komplett fehlender DB-Konfiguration weiterhin von Infrastrukturfehlern ueberdeckt werden.
- Kein automatischer CI-Zwang fuer PostgreSQL-Testlauf dokumentiert.
