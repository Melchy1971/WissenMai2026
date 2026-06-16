# Post-RC Plan

Stand: 2026-06-15
RC Gate: BLOCKED (2/7)
Quelle: `reports/current/post_rc_decision.json`

Regel: Keine M5c-Implementierung vor RC-Stabilisierung und externer Testentscheidung.

---

## Phase 0: RC-Stabilisierung (Pflicht vor allen anderen Optionen)

**Voraussetzung fuer alle weiteren Phasen.**

Drei Blocker muss vor der naechsten RC-Gate-Pruefung behoben werden:

### RC-PREREQ-01 — TEST_DATABASE_URL (Prioritaet 1, kritisch)

Betrifft: GATE-01 (local_final_gate), GATE-05 (report_integrity_final)

1. `TEST_DATABASE_URL` in `.env` setzen (PostgreSQL-Zugangsdaten)
2. `pytest tests/ -m "not external_env_only and not legacy_live_http"` ausfuehren
3. `report_integrity_v2` neu generieren
4. `final_gate_report.json` neu generieren
5. RC Gate neu pruef

Erwartetes Ergebnis nach Fix: GATE-01 PASS, GATE-05 PASS (5 weitere Blocker fallen weg durch Kaskade).

### RC-PREREQ-02 — AppShell NAV_ITEMS (Prioritaet 2, hoch)

Betrifft: GATE-02 (enduser_acceptance), GATE-04 (navigation_release_check)

Entscheidung erforderlich (PO): Masterplan anpassen oder AppShell korrigieren?

Option A (Masterplan anpassen):
- `/topics` und `/import` in `docs/final_navigation.md` aufnehmen
- `/chat` oder `/search` als kanonische Such-Route festlegen
- `/data-quality` in NAV_ITEMS behalten wie in Masterplan

Option B (AppShell korrigieren):
- `/search` durch `/chat` in NAV_ITEMS ersetzen
- `/data-quality` in NAV_ITEMS aufnehmen
- `/topics` und `/import` aus NAV_ITEMS entfernen

Unabhaengig von der Entscheidung: `final_navigation_release_check.json` und `enduser_acceptance_rc.json` nach der Korrektur neu ausfuehren.

### RC-PREREQ-03 — Routing-Sicherheit (Prioritaet 3, mittel)

Betrifft: GATE-03 (security_smoke)

1. AdminRoute-Wrapper in `routes.jsx` fuer `/admin/diagnostics` implementieren
2. Verbotene Routen (`/tools`, `/memory`, `/tasks`, `/projects`, `/agents`, `/collaboration`, `/governance`) aus `routes.jsx` entfernen oder hinter Admin-Guard legen
3. `rc_security_smoke_report.json` neu ausfuehren

---

## Option 1: RC-Stabilisierung (Unmittelbar nach Gate-Fix)

**Zeitrahmen: Nach RC-PREREQ-01 bis 03**

Ziel: RC Gate alle 7 Bedingungen PASS.

Schritte:
1. RC-PREREQ-01: TEST_DATABASE_URL + pytest
2. RC-PREREQ-02: NAV_ITEMS Entscheidung + Korrektur
3. RC-PREREQ-03: Router-Guard
4. Alle RC-Reports neu ausfuehren
5. RC Gate re-run

Ergebnis bei Erfolg: `release_candidate_gate.json` = RELEASE_CANDIDATE

---

## Option 2: Externe Umgebungstests

**Voraussetzung: RC-Stabilisierung (Option 1) abgeschlossen.**

Ziel: External Env Gate NOT_RUN -> PASS.

72 Tests in 6 Dateien (`tests/api/test_gui_backend_endpoints.py` etc.) gegen laufendes System ausfuehren:

```bash
pytest tests/api -m "external_env_only or legacy_live_http"
```

Anforderungen:
- Backend laeuft (`http://localhost:8000`)
- TEST_DATABASE_URL gesetzt
- Datenbasis geseedet

Ergebnis bei Erfolg: `external_env_gate.json` = PASS (derzeit NOT_RUN, blockiert RC nicht, aber fuer vollstaendige Freigabe relevant).

---

## Option 3: Installer / Deployment

**Voraussetzung: RC-Stabilisierung + Externe Tests abgeschlossen.**

Ziel: Reproduzierbares Deployment-Paket (lokal + Staging).

Scope:
- `install.md` und `start.md` gegen frische Installation verifizieren
- `dev_bootstrap.ps1` vollstaendig testen
- Optionale Docker-Compose-Konfiguration
- Deployment-Checkliste erstellen

---

## Option 4: M5c Cleanup Dry-Run Planung

**Voraussetzung: RC-Stabilisierung abgeschlossen. Externe Testentscheidung getroffen.**

**Nicht vor diesen Voraussetzungen.**

Scope: Nur Planung und Dry-Run-Vorbereitung, keine Implementierung.

- `m5c_start_gate.json` Gate-Bedingungen klaren
- PO-Sign-off auf `reports/current/cleanup_governance_boundary.json` einholen
- Dry-Run-Proposal ausarbeiten (ein Proposal = ein Kandidat, ein Approval)
- PROHIBIT-02 / PROHIBIT-06 / PROHIBIT-08 aktiv bis GO erteilt

GO-Bedingungen (alle erforderlich):
1. `m5c_start_gate.json` = PASS
2. `cleanup_governance_boundary.json` PO-Sign-off
3. RC-Stabilisierung abgeschlossen
4. Externe Testentscheidung getroffen

---

## Option 5: Nutzerfeedback

**Parallel zu RC-Stabilisierung moeglich.**

Scope: Strukturierte Rueckmeldung zu den 10 Enduser-Flows (S01-S10).

Fokus auf die blockierten Flows:
- S04 Suche: /search vs /chat — welche Erwartung haben Nutzer?
- S08 Data Quality: Nav-Eintrag fehlt — kritisch fuer Nutzerakzeptanz?

Ergebnis: Entscheidungsgrundlage fuer RC-PREREQ-02 (Masterplan vs. AppShell).

---

## Nicht-Optionen (gesperrt)

- M5c Implementierung vor RC-Stabilisierung: **GESPERRT**
- Repair/Cleanup-Aktionen: **GESPERRT** (PROHIBIT-02, PROHIBIT-06, PROHIBIT-08)
- 100%-Abschluss-Claim: **NICHT MOEGLICH** solange M5c und M5d offen

---

## Empfohlene Reihenfolge

```
RC-PREREQ-01 (TEST_DATABASE_URL)
  -> RC-PREREQ-02 (NAV-Entscheidung)
  -> RC-PREREQ-03 (Router-Guard)
  -> RC Gate re-run
  -> Option 1 abgeschlossen: RELEASE_CANDIDATE

DANN: Option 5 (Nutzerfeedback) parallel moeglich
DANN: Option 2 (Externe Tests) wenn RC stabil
DANN: Option 3 (Installer) wenn Externe Tests PASS
DANN: Option 4 (M5c Dry-Run Planung) zuletzt
```
