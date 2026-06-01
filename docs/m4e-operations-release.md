# M4e Operations Release Gate

Stand: 2026-05-29
Gate-Report: `reports/current/m4e_operations_release_gate.json`
Vorgaenger-Report: `reports/current/m4e_operations_release_report.json`

> Dieses Dokument ist die verbindliche Spezifikation des M4e Operations Release Gates.
> Freigabe-Entscheidungen werden ausschliesslich aus `reports/current/m4e_operations_release_gate.json` abgeleitet.

---

## Zweck

Das M4e Operations Release Gate klaert, was M5-Implementierung noch blockiert.
M4e Minimal (Backup/Restore-Nachweis) ist notwendige Basis, reicht allein aber nicht fuer die M5-Freigabe.
Dieses Gate prueft alle operativen Voraussetzungen vor dem ersten M5-Slice.

---

## In-Scope (9 Gate-Regeln)

| # | Regel-ID | Anforderung | Status |
|---|---|---|---|
| 1 | `m4e_ops_backup_createable` | Backup erzeugbar | siehe Gate-Report |
| 2 | `m4e_ops_restore_verified` | Restore validiert | siehe Gate-Report |
| 3 | `m4e_ops_reindex_after_restore` | Reindex nach Restore | siehe Gate-Report |
| 4 | `m4e_ops_health_diagnostics_read_only` | Health/Diagnostics read-only | siehe Gate-Report |
| 5 | `m4e_ops_runbook` | Recovery Runbook vorhanden | siehe Gate-Report |
| 6 | `m4e_ops_auth_seed_bootstrap_documented` | Auth/Seed Bootstrap dokumentiert | siehe Gate-Report |
| 7 | `m4e_ops_db_bootstrap_documented` | DB Bootstrap dokumentiert | siehe Gate-Report |
| 8 | `m4e_ops_recovery_commands_documented` | Recovery-Kommandos dokumentiert | siehe Gate-Report |
| 9 | `m4e_ops_no_mutating_admin_without_governance` | Keine mutierenden Adminaktionen ohne Governance | siehe Gate-Report |

---

## Regelspezifikationen

### 1. Backup erzeugbar

Ein vollstaendiger Backup-Lauf (DB-Dump + Originaldateien + Konfigurationsartefakt) muss ueber den CLI-Pfad ausloesbar sein.

**Abnahmekriterien:**
- `python -m app.cli backup create` schliesst ohne Fehler ab
- Backup-Manifest liegt vor und ist maschinenlesbar
- DB-Dump ist vollstaendig (alle relevanten Tabellen)

**Nachweise:** `reports/current/m4e_backup_restore_truth.json`, `docs/runbooks/backup-restore.md`

---

### 2. Restore validiert

Ein Restore auf eine leere Zielumgebung muss gegen eine echte lokale PostgreSQL-DB verifiziert werden. Nachweisquelle: `reports/current/m4e_operations_release_gate.json`.

**Abnahmekriterien:**
- `python -m app.cli backup restore` schliesst ohne Fehler ab
- Restore-Verifikation bestaetigt Vollstaendigkeit: Dokumente, Versionen, Chunks, Citations, Jobs
- Exit-Code 0 im Restore-Truth-Report

**Nachweise:** `reports/current/m4e_backup_restore_truth.json`, `docs/runbooks/backup-restore.md`, `docs/runbooks/disaster-recovery.md`

---

### 3. Reindex nach Restore

Nach jedem Restore muss ein Reindex als Pflichtschritt ausgefuehrt werden, bevor der Dienst den regulaeren Betrieb aufnimmt.

**Abnahmekriterien:**
- Reindex-Governance-Runbook beschreibt den Schritt explizit
- `python -m app.cli m5 retrieval-benchmark --trigger restore` laeuft nach Reindex
- `stale_index_growth = 0` nach Reindex

**Nachweise:** `reports/current/m4e_backup_restore_truth.json`, `docs/runbooks/reindex-governance.md`

---

### 4. Health/Diagnostics read-only

Diagnose-Endpunkte sind verfuegbar. Mutierende Aktionen ueber die GUI sind nicht zugelassen.

**Abnahmekriterien:**
- `GET /health` und `GET /health/db` liefern korrekte Antworten
- Admin-Diagnostics-GUI zeigt Systemzustand, loest aber keine Mutationen aus
- Kein Repair-, Cleanup- oder Reindex-Button ohne Governance-Freigabe

**Nachweise:** `reports/current/frontend_full_suite_staged_report.json`, `docs/m4d-admin-diagnostics.md`

---

### 5. Recovery Runbook vorhanden

Fuer Backup/Restore, Disaster Recovery und Reindex-Governance muss je ein ausfuehrbares Runbook vorhanden sein.

**Abnahmekriterien:**
- `docs/runbooks/backup-restore.md`: Schritt-fuer-Schritt-Ablaeufe
- `docs/runbooks/disaster-recovery.md`: Totalausfall und Datenwiederherstellung
- `docs/runbooks/reindex-governance.md`: Voraussetzungen und Nachweise
- `docs/runbooks/m5-operations-model.md`: laufende Betriebschecks

---

### 6. Auth/Seed Bootstrap dokumentiert (neu)

Der Ablauf zum Anlegen des Admin-Users, Seed des initialen Workspace und Verifikation von Login und Workspace-Isolation muss dokumentiert und per Truth-Report nachgewiesen sein.

**Abnahmekriterien:**
- `scripts/dev_bootstrap.ps1` fuehrt `seed_auth.py` und `check_auth_bootstrap.py` aus
- `check_auth_bootstrap.py` schliesst mit Exit-Code 0 ab
- `reports/current/m4a_auth_truth.json`: PASS, collected > 0
- `docs/operations.md` beschreibt Seed-Credentials als Single Source of Truth

**Nachweise:** `reports/current/m4a_auth_truth.json` (PASS, 43/43), `docs/operations.md`, `scripts/dev_bootstrap.ps1`

---

### 7. DB Bootstrap dokumentiert (neu)

Der Ablauf zur DB-Verbindungspruefung und Schema-Migration (alembic upgrade head) muss dokumentiert sein. Die Ausfuehrungsreihenfolge darf nicht von implizitem Entwicklerwissen abhaengen.

**Abnahmekriterien:**
- `scripts/dev_bootstrap.ps1` fuehrt DB-Check und `alembic upgrade head` in definierter Reihenfolge aus
- Reihenfolge (ENV laden → DB-Verbindung pruefen → migrate → seed → smoke-check) ist dokumentiert
- Fehler in jedem Schritt ergibt Exit != 0 und klare Fehlermeldung
- Optionale Flags (`-SkipSeed`, `-SkipSmoke`, `-DryRun`) sind beschrieben

**Nachweise:** `docs/operations.md`, `scripts/dev_bootstrap.ps1`

---

### 8. Recovery-Kommandos dokumentiert

Alle Recovery-Kommandos muessen mit konkreten CLI-Aufrufen, Parametern und erwarteten Ausgaben dokumentiert sein.

**Abnahmekriterien:**
- Jedes Runbook enthaelt ausfuehrbare Befehle mit konkreten Parametern
- Kein Recovery-Schritt erfordert undokumentiertes Kontextwissen
- Fehlerfaelle und Rollback-Pfade sind beschrieben

**Nachweise:** `docs/runbooks/backup-restore.md`, `docs/runbooks/disaster-recovery.md`, `docs/runbooks/reindex-governance.md`

---

### 9. Keine mutierenden Adminaktionen ohne Governance

Cleanup, Reindex, Repair und Restore duerfen nicht ohne expliziten Freigabepfad ausgefuehrt werden.

**Abnahmekriterien:**
- Admin-GUI loest keine destructiven Aktionen aus (M4d ist read-only)
- Jede Mutation: Runbook + Dry-Run + Freigabe
- Audit-Log-Eintrag fuer jede mutierende Aktion ist Pflicht

**Nachweise:** `docs/m4d-admin-diagnostics.md`, `docs/runbooks/m5-operations-model.md`, `docs/runbooks/reindex-governance.md`

---

## Out-of-Scope

| Bereich | Begruendung |
|---|---|
| Automatische Cloud-Backups | Nicht V1-kritisch; kein lokaler Betriebspfad erfordert Cloud-Ziele |
| Inkrementelle Backups | Vollbackup ist ausreichend fuer lokalen Minimal-Scope |
| Zero-Downtime Restore | Lokaler Betrieb erlaubt Wartungsfenster |
| Vollautomatische Repair Actions | Repair bleibt explizit ausgeloest; kein Auto-Repair ohne Audit |

---

## Gate-Entscheidung

Gate-Status: PASS (9/9 Regeln erfuellt, siehe `reports/current/m4e_operations_release_gate.json`)
M5-Implementierung: GO (alle Voraussetzungen erfuellt, siehe `reports/current/m4e_operations_release_gate.json`)

Gate-Report: `reports/current/m4e_operations_release_gate.json`

Ein einzelner FAIL in irgendeiner Regel blockiert die M5-Implementierungsfreigabe vollstaendig.
