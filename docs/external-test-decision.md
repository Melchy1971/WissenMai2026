# Externe Testentscheidung

Stand: 2026-06-15
Quelle: `reports/current/external_test_decision.json`

## Entscheidung

**EXT-OPT-2: Erst weitere RC-Stabilisierung**

Externe Tests koennen nicht gestartet werden. RC Gate ist BLOCKED (2/7). Voraussetzung fuer externe Tests ist RC Gate = RELEASE_CANDIDATE (7/7).

## Prerequisite-Status

| Pruefpunkt | Erforderlich | Aktuell |
|---|---|---|
| RC Gate | RELEASE_CANDIDATE (7/7) | BLOCKED (2/7) |
| RC Stabilization Gate | PASS (6/6) | BLOCKED (1/6) |
| Deployment Readiness | Keine BLOCKED-Checks | BLOCKED (DRC-01, DRC-03) |

## Optionen

| Option | Status | Begruendung |
|---|---|---|
| EXT-OPT-1: Externe Tests starten | BLOCKED | RC Gate nicht RELEASE_CANDIDATE |
| EXT-OPT-2: RC-Stabilisierung fortsetzen | ACTIVE | Korrekte Reihenfolge |
| EXT-OPT-3: Deployment vorbereiten | BLOCKED | Deployment Readiness BLOCKED |
| EXT-OPT-4: Pause | NICHT EMPFOHLEN | Fixes bekannt, Pause ohne Mehrwert |

## Naechste Schritte (Minimaler Pfad)

1. `TEST_DATABASE_URL` in `.env` setzen (RCB-001)
2. `.\scripts\run_final_gate.ps1` ausfuehren
3. PO-Entscheidung zu NAV_ITEMS: Option A (Masterplan anpassen) oder Option B (Code anpassen) (RCB-002)
4. Router-Guard fuer `/admin/diagnostics` implementieren (RCB-003)
5. RC Gate re-run -> Ziel: RELEASE_CANDIDATE (7/7)
6. Nach RELEASE_CANDIDATE: Externe Testentscheidung neu auswerten (EXT-OPT-1 freigeschaltet)

## Scope Externe Tests (zur Information)

- 72 Tests in 6 Dateien
- Marker: `external_env_only`, `legacy_live_http`
- Ausfuehrung: `pytest tests/api -m 'external_env_only or legacy_live_http' -v --tb=short`
- Geschaetzte Dauer: ~5 Minuten
- Testplan: `docs/external-env-testplan.md`, `reports/current/external_env_testplan.json`

## Invarianten

- M5c-Implementierung: LOCKED (kein GO ohne RELEASE_CANDIDATE + ext. Testentscheidung + m5c_start_gate PASS + PO-Sign-off)
- Drift Detection: Read-Only (PROHIBIT-02, PROHIBIT-06)
- Repair-Aktionen: NO_GO
