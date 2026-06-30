# PRI-8 Execution Plan — Blockerbehebung

**Sprint:** PRI-8 (Name: Blockerbehebung)
**Erstellt:** 2026-06-30
**Trigger:** GA Final Gate = BLOCKED (PRI-7, 2026-06-17)
**Ziel:** GA_READY — Product Maturity ≥ 90
**Quellen:** `README.md`, `reports/current/masterplan_status.json`, `reports/current/ga_final_gate_report.json`, `docs/pri8_backlog.md`
**Repository-Basis:** `origin/main` @ 888c668 (lokal == origin, 0 ahead / 0 behind)

---

## 1. Eingefrorener Status (PRI-7-Abschluss)

| Größe | Wert | Quelle |
|-------|------|--------|
| Release-Status | **BLOCKED** | masterplan_status.json, ga_final_gate_report.json |
| Product Maturity | **68.7 / 100** | masterplan_status.json (`product_maturity_score`), ga_final_gate_report.json (`current_maturity`) |
| GA-Schwellwert | **90** | ga_final_gate_report.json (`ga_threshold`) |
| Maturity-Gap | **21.3** | ga_final_gate_report.json (`maturity_gap`) |
| GA-Kriterien | 3 PASS / 4 FAIL / 3 BLOCKED (10 gesamt) | ga_final_gate_report.json (`summary`) |
| Gold Path | 8/8 PASS | masterplan_status.json |
| Verdict-Regel | BLOCKED hat Vorrang vor FAIL | ga_final_gate_report.json (`verdict_reason`) |

### Datenklärung Maturity (PO-Entscheidung 2026-06-30)

- **Verbindlich: 68.7 / 100.** Begründung: 68.7 ist exakt der Mittelwert der 11 dokumentierten Dimensionen aus `pri8_backlog.md` (Summe 756 / 11 = 68.7) und stimmt mit `masterplan_status.json` (`product_maturity_score`) und `ga_final_gate_report.json` (`current_maturity`) überein.
- **Zu korrigieren (Schritt 8):** Der Wert „80/100" in `ga_final_gate_report.json` → Kriterium GA-02 (`detail`) und `blocking_items` ist nicht aus der Dimensionstabelle reproduzierbar und gilt als veraltet. Er ist beim Report-Neulauf auf 68.7 zu vereinheitlichen, damit der Gesamtscore nicht seiner eigenen Aufschlüsselung widerspricht.

---

## 2. Offene Blocker

| ID | Typ | Titel | Owner | Aufwand | Entsperrt (GA-Kriterium) |
|----|-----|-------|-------|---------|--------------------------|
| SCGB-01 | EXTERN | TEST_DATABASE_URL bereitstellen | DevOps | — | GA-06, GA-07, GA-10 |
| SCGB-02 | EXTERN | NAV_ITEMS | PO | — | — (nicht GA-blockend laut Gate) |
| GA-PERF-01 | INTERN | GIN-Index auf `document_chunks.search_vector` | Dev | S | GA-05 |
| GA-SEC-01 | INTERN | Content Security Policy / Security-Header | Dev | S | GA-03 |
| GA-OBS-01 | INTERN | Prometheus `/metrics` + strukturiertes Logging | Dev | M | GA-08 |
| GA-TEST-01 | INTERN+EXTERN | Integrations-Test-Suite | Dev (nach DevOps) | M | GA-10 |

**Abhängigkeitskette:** SCGB-01 (DevOps) ist die Wurzel. GA-06, GA-07, GA-10 bleiben BLOCKED, solange `TEST_DATABASE_URL` nicht in der CI verfügbar ist. GA-TEST-01 ist ohne SCGB-01 nicht abschließbar — nur vorbereitbar.

---

## 3. GA-Kriterien-Snapshot (PRI-7)

| ID | Kriterium | Status | Adressiert durch |
|----|-----------|--------|------------------|
| GA-01 | Gold Path 8/8 | PASS | — |
| GA-02 | Maturity ≥ 90 | FAIL | GIN-Index, CSP, Integrationstests |
| GA-03 | Security | FAIL | GA-SEC-01 |
| GA-04 | Technical ID Leaks = 0 | PASS | — |
| GA-05 | Performance | FAIL | GA-PERF-01 |
| GA-06 | Backup | BLOCKED | SCGB-01 |
| GA-07 | Restore | BLOCKED | SCGB-01 |
| GA-08 | Monitoring | FAIL | GA-OBS-01 |
| GA-09 | Operations Documentation | PASS | — |
| GA-10 | Regression Suite | BLOCKED | SCGB-01 / GA-TEST-01 |

---

## 4. Ausführungsreihenfolge PRI-8

Reihenfolge wie vorgegeben. Jeder Schritt: Ziel, betroffenes GA-Kriterium, Abhängigkeit, Definition of Done. **DoD-Standard global: Abnahme erst bei fehlerfreiem Live-Lauf — kein Mock, kein Stub.**

### Schritt 1 — GIN-Index

- **Ziel:** GIN-Index auf `document_chunks.search_vector` per Alembic-Migration.
- **Blocker / Kriterium:** GA-PERF-01 → GA-05.
- **Abhängigkeit:** keine (sofort umsetzbar).
- **DoD:** Migration angelegt und `alembic upgrade head` fehlerfrei; Index in DB nachgewiesen (`\d+ document_chunks`); Suchanfrage bei realem Datenbestand mit Query-Plan-Beleg (Index statt Seq-Scan).
- **Hinweis:** `CREATE INDEX CONCURRENTLY` läuft nicht in einer Alembic-Transaktion — Migration entsprechend mit autocommit/`op.execute` außerhalb Transaktion bauen.

### Schritt 2 — CSP / Security-Header

- **Ziel:** `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` als Middleware.
- **Blocker / Kriterium:** GA-SEC-01 → GA-03.
- **Abhängigkeit:** keine.
- **DoD:** Header in Live-Response nachgewiesen (curl/Browser-DevTools); bestehende Security-Tests grün; keine Regression bei Frontend-Assets durch CSP (`style-src`/`script-src` real geprüft).

### Schritt 3 — Observability

- **Ziel:** Prometheus `/metrics` (Counter/Histogram/Gauge) + strukturiertes JSON-Logging.
- **Blocker / Kriterium:** GA-OBS-01 → GA-08 (teilweise).
- **Abhängigkeit:** keine.
- **DoD:** `/metrics` liefert valides Prometheus-Format im Live-Lauf; Request-Metriken zählen real hoch; Logausgabe ist strukturiertes JSON. Neue Dependencies dokumentiert.

### Schritt 4 — Readiness Health

- **Ziel:** `/health/ready` (Dependency-Check: DB, Migrationen) ergänzend zu `/health`.
- **Blocker / Kriterium:** GA-08 (Rest).
- **Abhängigkeit:** keine.
- **DoD:** `/health/ready` antwortet im Live-Lauf mit korrektem Zustand bei DB erreichbar **und** bei DB nicht erreichbar (beide Fälle getestet).

### Schritt 5 — Integrationstest-Vorbereitung

- **Ziel:** Integrations-Test-Suite lauffähig machen (Struktur, Fixtures, CI-Hook), **ohne** Abschluss.
- **Blocker / Kriterium:** GA-TEST-01 → GA-10.
- **Abhängigkeit:** **GESPERRT durch SCGB-01 (DevOps).** Ohne `TEST_DATABASE_URL` nicht ausführbar.
- **DoD (PRI-8-Teil):** Suite startet lokal gegen eine erreichbare Test-DB; CI-Job vorhanden, der bei gesetztem `TEST_DATABASE_URL` automatisch läuft. **Voller Abschluss bleibt offen bis SCGB-01.**

### Schritt 6 — Backup/Restore-Testfähigkeit

- **Ziel:** Backup- und Restore-Prozeduren als ausführbare Tests vorbereiten.
- **Blocker / Kriterium:** GA-06, GA-07.
- **Abhängigkeit:** **GESPERRT durch SCGB-01.**
- **DoD (PRI-8-Teil):** Test-Skripte vorhanden und gegen erreichbare Test-DB lauffähig; Prozedur dokumentiert. **Nachweis „getestet" erst nach SCGB-01.**

### Schritt 7 — Pagination-Risiko

- **Ziel:** Risiko großer Ergebnismengen (Such-/Listen-Endpunkte ohne Begrenzung) härten.
- **Blocker / Kriterium:** kein benanntes GA-Kriterium — Scalability-/Performance-Härtung.
- **Abhängigkeit:** keine.
- **Scope-Grenze:** **nur** Begrenzung/Pagination bestehender Endpunkte, **keine** neuen Features. Wenn kein konkreter Endpunkt betroffen ist, als „kein Befund" dokumentieren statt Scope zu erweitern.
- **DoD:** betroffene Endpunkte mit Limit/Offset oder Cursor; Verhalten bei großer Menge im Live-Lauf belegt.

### Schritt 8 — Statusreports

- **Ziel:** Reports nach Umsetzung neu erzeugen: `product_maturity_v3`/-Nachfolger, `release_gate.json`, `masterplan_status.json` (Sprint → PRI-8, Stati der Blocker).
- **Abhängigkeit:** Schritte 1–7.
- **DoD:** Reports spiegeln den realen Stand; geschlossene Blocker als geschlossen markiert; offene (SCGB-01-abhängige) als offen.

### Schritt 9 — Dokumentation

- **Ziel:** README-Statusabschnitt, `docs/status.md`, `docs/generated/status_section.md`, Changelog auf PRI-8 aktualisieren.
- **Abhängigkeit:** Schritt 8.
- **DoD:** Dokumente konsistent mit den neuen Reports; keine widersprüchlichen Maturity-Zahlen mehr (siehe §1-Datenklärung).

### Schritt 10 — Gate-Recheck

- **Ziel:** GA Final Gate erneut ausführen.
- **Abhängigkeit:** Schritte 1–9.
- **DoD:** `ga_final_gate_report.json` neu erzeugt; Verdict belegt.
- **Abschlussregel (aus pri8_backlog.md):**
  - Maturity ≥ 90 → **GA_READY**: Release-Tag v1.0, Changelog, Installationsanleitung finalisieren.
  - Maturity < 90 → **PRI-9 Qualitätserhöhung**.

---

## 5. Realistische Zielbewertung

Die Maturity-Prognose in `pri8_backlog.md` summiert nach **vollständiger** PRI-8-Umsetzung auf **~85.8/100**. Das liegt **unter** dem GA-Schwellwert 90. Die im selben Dokument stehende Formulierung „GA_READY > 90 möglich" ist durch die eigene Prognosezahl nicht gedeckt.

**Konsequenz für die Planung:** PRI-8 ist ein Blocker-Schließungs-Sprint, kein GA-Garant. Erwartbares Ergebnis des Gate-Rechecks (Schritt 10) ist **weiterhin < 90**, sofern keine zusätzlichen Dimensions-Gewinne über die Prognose hinaus erzielt werden. PRI-9 ist einzuplanen, nicht als Ausnahme zu behandeln. Zusätzlich ist GA-Kriterium GA-02 erst nach Schließung der SCGB-01-Kette (GA-06/07/10) überhaupt aus dem BLOCKED-Zustand zu holen — die internen Schritte 1–4 allein heben den Gesamtstatus nicht aus BLOCKED.

---

## 6. Scope-Grenzen (verbindlich)

- **Keine Feature-Erweiterungen außerhalb PRI-8.** Insbesondere ausgeschlossen: Importcenter-Erweiterung (Ordner-Import, PST-Import) — 1.1-Kandidat, separat dokumentiert in `OUTPUTS/Importcenter-Erweiterung/`.
- **Keine Cleanup-/Repair-Aktionen** (PROHIBIT-02, PROHIBIT-06, PROHIBIT-08; M5c bleibt NO_GO).
- **Keine Secrets committen.** Hinweis: Im aktuellen `README.md` liegen Klartext-Zugangsdaten und eine DB-Host-IP. Das ist ein bestehender Befund außerhalb PRI-8 und vor weiterer Arbeit zu bereinigen (Passwort rotieren, aus Datei und History entfernen). Dieser Plan übernimmt keine Credentials.
- **Drift bleibt read-only.**

---

## 7. Geänderte/erzeugte Dateien dieses Schritts

- **Neu:** `docs/pri8_execution_plan.md` (dieses Dokument).
