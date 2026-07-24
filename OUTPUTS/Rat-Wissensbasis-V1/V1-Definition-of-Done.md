# V1 Definition of Done — Wissensbasis (Multi-User)

Stand: 2026-07-24. Grundlage: Scope-Entscheidung Markus + Code-Verifikation.

## Ziel (verbindlich)

- **Zielnutzer:** das Unternehmen, mehrere User.
- **Fertig:** Jeder User hat einen **eigenen Bereich** und es gibt einen **gemeinsamen Bereich**.

### Operationalisiert (testbar)

1. Jeder User authentifiziert sich individuell; kein Default-User im Request-Pfad.
2. Jeder User hat genau einen privaten Workspace; nur er liest/schreibt dort.
3. Genau ein gemeinsamer Workspace, in dem alle User Mitglied sind; Lesen für alle Mitglieder, Schreiben nach Rolle.
4. Harte Isolation: kein User sieht fremde private Bereiche — über API, Suche, Chat und Retrieval.
5. Onboarding: neuen User anlegen → privaten Workspace automatisch erzeugen → Mitgliedschaft im gemeinsamen Workspace.
6. Nachweis gegen echte PostgreSQL (SCGB-01), inklusive Backup/Restore der Multi-User-Daten.

## Fundament, das schon steht (Code-verifiziert 2026-07-24)

- Datenmodell trägt Multi-User: `Workspace`, `User`, `WorkspaceMembership` mit Rollen-Check `owner|admin|member` (`app/models/documents.py`). Privat = 1 Workspace/User, gemeinsam = 1 Workspace mit mehreren Memberships. **Kein Schema-Neubau nötig.**
- Auth: individueller Login lädt Memberships (`app/services/auth.py`: `login`, `authenticate`, `revoke_session`).
- Isolations-Primitiv vorhanden: `require_workspace_member`-Dependency wird bereits in Routern verwendet (z. B. `collaboration_gui.py`) — die Membership-Prüfung als Baustein existiert.
- `default_user_id`/`default_workspace_id` stehen nur noch in Backup-Metadaten (`backup_restore.py`), **nicht** im Request-/Dependency-Pfad — die M4a-Stop-Regel „kein Default-User in Prod-Requests" ist im Request-Pfad erfüllt.
- Workspace-scoped Read/Search/Chat ist laut Masterplan/Code vorhanden.

## Lücken zu „fertig" (die echte V1-Blockerliste) — verifiziert 2026-07-24

- [ ] **Provisioning fehlt (bestätigt):** Kein `create_user` / `create_workspace` / `add_member` irgendwo in `app/`. `auth.py` hat nur `login`/`logout`/`me`, `admin.py` nur Diagnose/Reindex/Backup. User/Workspace entstehen heute **ausschließlich** über `backend/scripts/seed_auth.py` — und das seedet **einen** Default-User (dich: `mdickscheit@…`). Das System ist heute faktisch Single-User-per-Seed. Onboarding mehrerer User = **neu zu bauen**.
- [ ] **Gemeinsamer Bereich existiert nicht als Dokument-Feature (bestätigt):** `collaboration_gui.py` ist eine In-Memory-Agenten-Kollaboration (`_runs`, `_teams` sind Modul-Listen, keine DB); „shared_workspace_snapshot" ist ein Feld in einem Run-Payload mit Redaction, **kein** geteilter Dokument-Workspace. Der gemeinsame Bereich ist **neu zu bauen** (technisch: 1 Workspace mit Membership aller User + Schreibregeln).
- [ ] **Isolationstests:** privat vs. fremd vs. gemeinsam über API/Suche/Chat/Retrieval, gegen echte DB. Baustein `require_workspace_member` ist da; die Regeln + Tests fehlen.
- [ ] **SCGB-01:** Truth-Lauf gegen die echte Test-DB (von dir bereitgestellt).
- [ ] **m4e Backup/Restore-Truth reparieren:** Test bricht beim Import (`create_backup` etc. entfernt → `BackupRestoreService`). Multi-User-Daten müssen wiederherstellbar sein — jetzt V1-kritisch. Siehe `EVIDENCE.md`, Fund 2.
- [ ] **GA-Härtung, die Multi-User schützt:** CSP + sichere Sessions (jetzt zu Recht V1, nicht mehr Gold-Plating).

## Blocker-Re-Split gegen das neue Ziel

**V1-kritisch** (war „GA/optional", ist jetzt Pflicht, weil es Isolation/Recovery mehrerer User betrifft):

- M4a Auth hart + Workspace-Isolation (privat + gemeinsam)
- User-/Workspace-Provisioning + Membership-Verwaltung
- SCGB-01 + Integrationstests (GA-TEST-01)
- m4e Backup/Restore-Truth (Fix + grün)
- CSP / Session-Härtung (GA-SEC-01)

**Deferred** (nicht „fertig"-relevant für diese DoD):

- KI-Analyse-Provider-Produktisierung (Ollama/OpenAI/Gemini)
- Topics, Export/PDF, Drift-Analytics-Dashboards, Importcenter-PST
- Embeddings / Vektorsuche
- Prometheus / Observability (Betriebs-Kür, kein „fertig"-Kriterium — außer du betreibst es zentral für die Firma, dann wieder rein)

## Widerspruch im Masterplan, der aufzulösen ist

Der Masterplan deklariert Multi-User heute **explizit als NICHT-V1**. Deine Definition kehrt das um. Drei Stellen müssen bewusst überschrieben werden, sonst bleibt genau die Drift, die der Rat kritisiert hat:

1. Leitentscheidung (Abschnitt 1): „Mehrbenutzer: Datenmodell vorbereiten, Logik später" → **jetzt V1-Ziel**.
2. V1-Scope „Explizit nicht in V1: komplexe Rollen-/Rechteverwaltung" → präzisieren: einfache Rollen (owner/member) + gemeinsamer Bereich **sind** V1; Enterprise-Feinrechte bleiben raus.
3. M4 Nicht-Scope: „Multi-User-Collaboration" → **gemeinsamer Bereich ist jetzt V1-Pflicht**.

## Erster Schritt

Die beiden Ziel-Sätze + diese DoD als klar markierten Block an den Kopf des V1-Scope in `masterplan.md` eintragen und die drei widersprechenden Stellen korrigieren. Danach die Blockerliste im Repo (`docs/pri8_backlog.md`) gegen V1-kritisch/deferred neu ordnen.
