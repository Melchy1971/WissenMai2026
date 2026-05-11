# Masterplan Completion Matrix

Stand: 2026-05-11
Grundlage: Code- und Teststand im Repository, `reports/postgres_truth/latest.json` (Commit b07798e, 33/33 postgres_truth bestanden).

Methodische Hinweise:
- **Feature %** = Anteil implementierter Scope-Punkte laut Masterplan (nicht Code-Coverage)
- **Tests %** = Breite und Tiefe der existierenden Tests (Unit + API + Integration, ohne Truth)
- **Truth % ** = Anteil des Scope, der durch postgres_truth-Tests auf echter PostgreSQL-DB verifiziert ist
- **Docs %** = Vollständigkeit und Aktualität der zugehörigen Dokumentation
- **Gate-fähig %** = realer Bereitschaftsgrad für ein maschinell durchgesetztes Release-Gate
- Alle Werte sind Einschätzungen auf Basis des vorliegenden Codes — keine Code-Coverage-Tool-Ausgaben

---

## Completion Matrix

| Bereich | Feature | Tests | Truth | Docs | Gate-fähig |
|---|---|---|---|---|---|
| M0 Fundament | 100% | 85% | 40% | 90% | 75% |
| M1 Import/Parser | 70% | 80% | 40% | 80% | 55% |
| M2 Read API | 95% | 90% | 65% | 95% | 80% |
| M3a GUI Foundation | 80% | 45% | 0% | 65% | 50% |
| M3b Search/Retrieval | 80% | 60% | 50% | 75% | 45% |
| M3c Chat/RAG | 75% | 70% | 55% | 70% | 45% |
| M4a Auth/Workspace | 70% | 65% | 75% | 75% | 55% |
| M4b Upload/Queue | 80% | 70% | 65% | 75% | 55% |
| M4c Lifecycle | 80% | 65% | 65% | 70% | 60% |
| M4d Diagnostics read-only | 85% | 70% | 15% | 80% | 40% |
| M4d Diagnostics full | 5% | 10% | 0% | 60% | 0% |
| M4e Backup/Restore | 0% | 0% | 0% | 25% | 0% |
| M5 Systemreife | 3% | 0% | 0% | 15% | 0% |
| **Durchschnitt** | **63%** | **55%** | **36%** | **67%** | **43%** |

---

## Detail: Blocker und nächster Fix

### M0 — Fundament

| | |
|---|---|
| **Blocker** | CI ohne PostgreSQL-Pflichtlauf konfiguriert |
| **Nächster Fix** | GitHub Actions: PostgreSQL Service Container hinzufügen; `test_migrations.py` als Pflicht-Step |

### M1 — Import/Parser

| | |
|---|---|
| **Blocker 1** | `ocr_service.py`: Klasse hat nur `pass` — stiller Stub, kein explizites Signal wenn OCR gefordert wird |
| **Blocker 2** | `ki_provider.py`: Klasse hat nur `pass` — stiller Stub, KI-Normalisierung nie ausgeführt |
| **Blocker 3** | DOC-Parser benötigt lokales LibreOffice — nicht containerisierbar ohne Anpassung |
| **Nächster Fix** | `raise NotImplementedError` in beiden Stub-Klassen; DOC-Parser-Abhängigkeit in Docs explizit machen |

### M2 — Read API (Paket 5)

| | |
|---|---|
| **Blocker** | Pfad-Inkonsistenz: Code liefert unter `/documents`, Ziel-API ist `/api/v1/documents` |
| **Nächster Fix** | `/api/v1/documents` als Router-Präfix oder Alias implementieren |

### M3a — GUI Foundation

| | |
|---|---|
| **Blocker 1** | Kein Frontend-CI-Lauf (Vitest/Jest nicht in Pipeline) |
| **Blocker 2** | Auth-E2E nicht automatisiert getestet — route guard vorhanden, aber kein verifizierter Login→Redirect-Nachweis |
| **Nächster Fix** | `npm test` in CI aktivieren; AuthBootstrap-Test auf echten Login-Flow ausweiten |

### M3b — Search/Retrieval

| | |
|---|---|
| **Blocker 1** | `TEST_DATABASE_URL` nicht für CI konfiguriert — 16 Integrationstests werden regelmäßig geskippt |
| **Blocker 2** | Letzter dedizierter PostgreSQL-Lauf endete mit `ConnectionTimeout` gegen Ziel-DB |
| **Nächster Fix** | CI PostgreSQL Service Container; Integrationstests als Pflichtlauf ohne Skip-Toleranz |

### M3c — Chat/RAG

| | |
|---|---|
| **Blocker 1** | `ki_provider.py` = `pass` — kein echter LLM wired; alle Produktionspfade landen bei `FakeLLMProvider` |
| **Blocker 2** | Kein E2E-RAG-Test mit echter PostgreSQL-Datenbank und echtem Retrieval |
| **Nächster Fix** | KI-Provider-Interface dokumentieren als "requires production implementation"; Fake explizit als dev-only kennzeichnen |

### M4a — Auth/Workspace

| | |
|---|---|
| **Blocker 1** | `POST /api/v1/auth/logout` fehlt — kein Token-Revoke-Endpoint |
| **Blocker 2** | Frontend-Auth-E2E: Route Guard getestet, aber Login→Token→Request→Redirect-Flow nicht verifiziert |
| **Status Truth** | m4a_gate: 10 Tests, alle grün (100%) — starke Abdeckung für implementierte Features |
| **Nächster Fix** | Logout-Endpoint: `POST /auth/logout` mit Session-Revoke implementieren |

### M4b — Upload/Queue

| | |
|---|---|
| **Blocker** | `test_parallel_duplicate_imports_create_single_document` liegt in `tests/integration/`, nicht in `tests/postgres_truth/` — Race-Condition-Nachweis ist kein Pflichtgate |
| **Status Truth** | m4b_gate: 5 Tests, alle grün (100%) — Crash-Recovery und Retry abgedeckt |
| **Nächster Fix** | Race-Test nach `tests/postgres_truth/` verschieben und `@pytest.mark.m4b_gate` hinzufügen |

### M4c — Lifecycle

| | |
|---|---|
| **Blocker** | Kein direkter E2E-Test: Dokument archivieren → neues Chat-Retrieval gibt kein Ergebnis → Konsistenz nachgewiesen |
| **Status Truth** | m4c_gate: 8 Tests, alle grün (100%) — Search/Index-Konsistenz und source_status abgedeckt |
| **Nächster Fix** | postgres_truth-Test für `archive_document → chat_message_with_retrieval → no_hit` hinzufügen |

### M4d — Diagnostics read-only

| | |
|---|---|
| **Blocker** | Kein `@pytest.mark.m4d_gate` in der gesamten Test-Suite — Validator meldet Gate Score = `null` |
| **Bestand** | 7 Diagnostics-API-Tests + 8 Search-Index-API-Tests decken read-only-Kontrakt gut ab, sind aber nicht als Gate-Tests markiert |
| **Nächster Fix** | `@pytest.mark.m4d_gate` auf 3–4 bestehende Diagnostics-Tests in `test_m4_truth_flows.py` oder neuer Datei setzen |

### M4d — Diagnostics full

| | |
|---|---|
| **Status** | Bewusst blockiert — `POST /search-index/rebuild` liefert 501; alle mutierenden Admin-Aktionen fehlen |
| **Abhängigkeit** | Frühestens nach M4a + M4b + M4c Gate = PASS |
| **Nächster Fix** | Nicht im M4 Stabilization Sprint scope |

### M4e — Backup/Restore

| | |
|---|---|
| **Status** | Konzept in `docs/m4e-backup-restore.md`; kein Code vorhanden |
| **Nächster Fix** | Nach M4 Stabilization Sprint priorisieren; explizit aus V1-Muss-Scope heraushalten |

### M5 — Systemreife

| | |
|---|---|
| **Status** | Blockiert durch M4; Datenmodell-Vorbereitungen vorhanden |
| **Nächster Fix** | Warten auf `scripts/validate_m4_truth_gate.py` → `M4 Stabilization Gate = PASS` |

---

## Reale Gesamtbewertung

```
Feature-Fortschritt:   63%  ████████████░░░░░░░░
Testabdeckung:         55%  ███████████░░░░░░░░░
Truth-Validierung:     36%  ███████░░░░░░░░░░░░░
Dokumentation:         67%  █████████████░░░░░░░
Gate-fähig (Reife):    43%  ████████░░░░░░░░░░░░
```

**Kurzfassung:** Das System ist zu ~63% feature-complete im V1-Scope, aber nur zu ~43% production-gate-ready. Der größte Verlust entsteht durch die Truth-Validierungslücke (36%) — viele Features sind implementiert und grob getestet, aber ohne PostgreSQL-Pflichtnachweis.

Für den aktuell aktiven M4-Bereich (M4a–M4d read-only, Positionen 7–10):

```
M4 Feature:       79%  ████████████████░░░░
M4 Tests:         68%  █████████████░░░░░░░
M4 Truth:         55%  ███████████░░░░░░░░░
M4 Gate-fähig:    53%  ██████████░░░░░░░░░░
```

---

## Differenz Feature vs. Reife

| Bereich | Feature | Gate-fähig | Gap | Ursache |
|---|---|---|---|---|
| M0 Fundament | 100% | 75% | **-25%** | Kein CI-PostgreSQL-Pflichtlauf |
| M1 Import/Parser | 70% | 55% | **-15%** | Stille Stubs (OCR, KI-Provider) |
| M2 Read API | 95% | 80% | **-15%** | Pfad-Inkonsistenz; auth-Vollständigkeit |
| M3a GUI | 80% | 50% | **-30%** | Kein Frontend-CI; kein E2E-Auth-Test |
| M3b Search | 80% | 45% | **-35%** | Integrationstests regelmäßig geskippt |
| M3c Chat/RAG | 75% | 45% | **-30%** | Kein echter LLM; kein DB-E2E |
| M4a Auth | 70% | 55% | **-15%** | Logout fehlt; E2E-Frontend ungetestet |
| M4b Upload | 80% | 55% | **-25%** | Race-Test kein Pflichtgate |
| M4c Lifecycle | 80% | 60% | **-20%** | Chat-post-lifecycle-Test fehlt |
| M4d read-only | 85% | 40% | **-45%** | Kein m4d_gate-Marker → Gate Score null |
| M4d full | 5% | 0% | **-5%** | Bewusst blockiert |
| M4e Backup | 0% | 0% | 0% | Nicht implementiert |
| M5 | 3% | 0% | **-3%** | Blockiert |
| **Gesamt** | **63%** | **43%** | **-20%** | |

**Kritischer Befund:** M4d read-only hat den größten Gap (-45%) — das Feature ist zu 85% fertig, aber der Gate-Score ist `null`, weil kein einziger Test den `@pytest.mark.m4d_gate`-Marker trägt. Das ist ein Ein-Zeilen-Fix, der den Gate-fähig-Wert sofort auf ~80% hebt.

**Systemischer Befund:** Der zweitgrößte Gap-Treiber ist die fehlende CI-Pflicht für PostgreSQL. Sechs von dreizehn Bereichen haben Tests, die regulär geskippt werden oder nie in CI laufen — das macht ihre Truth-Validierungswerte strukturell niedrig, unabhängig von der Implementierungsqualität.

---

## Priorisierte Fixes für M4 Stabilization Sprint

Sortiert nach Impact/Aufwand-Verhältnis:

| Prio | Fix | Gap-Reduktion | Aufwand |
|---|---|---|---|
| 1 | `@pytest.mark.m4d_gate` auf bestehende Diagnostics-Tests | -45% → ~-5% für M4d | 30 min |
| 2 | Race-Test nach `postgres_truth/` verschieben + m4b_gate-Marker | Race-Condition RC-Blocker schließen | 1h |
| 3 | `logout` Endpoint implementieren | M4a vollständiger | 2h |
| 4 | Chat-post-lifecycle postgres_truth-Test | M4c Lifecycle-Chat-Gap schließen | 3h |
| 5 | `raise NotImplementedError` in OCR + KI-Provider Stubs | Silentes Fehlschlagen verhindern | 30 min |
| 6 | Frontend CI (Vitest) aktivieren | M3a Gate-fähig von 50% auf ~70% | 2h |
| 7 | CI PostgreSQL Service Container | M3b Truth von 50% auf ~80% | 4h |

Fixes 1–5 sind alle Voraussetzungen für `M4 Stabilization Gate = PASS`.
