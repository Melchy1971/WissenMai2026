# Fachkonzept — Block 1: User- und Workspace-Provisioning (Wissensbasis V1, Multi-User)

Stand: 2026-07-24
Autor: Markus (PO) / Erarbeitung Claude
Grundlage: verifizierter Code-Stand `backend/app` @ Head `20260618_0026`, V1-Definition-of-Done
Abnahmestandard: Abnahme erst bei fehlerfreiem Live-Lauf gegen echte PostgreSQL.

---

## 1. Zweck und Abgrenzung

Dieses Konzept beschreibt **Block 1** der Multi-User-V1: das Anlegen und Verwalten von Usern und Workspaces, inklusive automatischem Privatbereich und Mitgliedschaft im gemeinsamen Bereich.

- **In Scope:** User anlegen/deaktivieren, Privat-Workspace automatisch erzeugen, Mitgliedschaft im gemeinsamen Workspace, Rollen owner/admin/member, Admin-geschützte Verwaltung, Audit.
- **Nicht in diesem Block:** Schreib-/Leseregeln des gemeinsamen Bereichs im Detail (Block 2 „Gemeinsamer Bereich"), Self-Service-Registrierung, OAuth/SSO, Enterprise-Feinrechte, Passwort-Reset-Flow (nur Schnittstelle vorsehen).

---

## 2. Ist-Zustand (verifiziert)

- Datenmodell trägt Multi-User bereits: `workspaces`, `users`, `workspace_memberships` (Rollen `owner|admin|member`, Unique `(workspace_id, user_id)`).
- `users`: `id, display_name, login (unique), password_hash, is_active, is_default, created_at`.
- `workspaces`: `id, name, is_default, created_at` — **kein** Feld für „privat vs. gemeinsam" und **kein** Besitzer-Bezug.
- Auth vorhanden: `login`/`logout`/`me`, `AuthService.authenticate`, Dependency `require_workspace_member`, Rolle-basierte Adminprüfung (`ADMIN_REQUIRED`).
- Passwort-Hashing vorhanden: `hash_password(password, salt=…)`, Spalte `password_hash`.
- **Lücke:** kein `create_user` / `create_workspace` / `add_member` in `app/`. User/Workspace entstehen nur über `scripts/seed_auth.py` (seedet **einen** Default-User). System ist heute Single-User-per-Seed.

---

## 3. Fachliche Anforderungen (V1)

1. Ein Administrator kann neue User anlegen (`display_name`, `login`, Initialpasswort).
2. Beim Anlegen eines Users wird **automatisch genau ein Privat-Workspace** erzeugt; der User erhält dort Rolle `owner`.
3. Es existiert **genau ein gemeinsamer Workspace**; jeder aktive User wird beim Anlegen automatisch Mitglied (Default-Rolle `member`).
4. Ein Administrator kann Rollen im gemeinsamen Workspace ändern (`member` ↔ `admin`) und User deaktivieren.
5. Ein deaktivierter User kann sich nicht anmelden; seine Daten bleiben erhalten (kein Hard-Delete).
6. Kein Endpoint vertraut `workspace_id` oder `user_id` aus Query/Body als Identität — Identität kommt aus dem Auth-Kontext.
7. Kein produktiver Pfad nutzt Default-User/Default-Workspace.
8. Jede mutierende Aktion erzeugt einen Audit-Eintrag.

---

## 4. Bereichs- und Rollenmodell

| Bereich | Technisch | Mitgliedschaft | Rollen |
|---|---|---|---|
| Privat | 1 Workspace pro User | genau der Eigentümer | `owner` |
| Gemeinsam | 1 globaler Workspace | alle aktiven User | `admin` (verwaltet), `member` (nutzt) |

Regel: Rolle `owner` existiert nur im jeweiligen Privat-Workspace. Im gemeinsamen Workspace gibt es nur `admin`/`member`. Das ist über die bestehende Check-Constraint (`owner|admin|member`) abbildbar, ohne Schemaänderung an der Constraint.

---

## 5. Datenmodell-Änderungen (additiv, eine Migration)

`workspaces` wird um zwei Felder ergänzt:

- `kind` `String(16)`, NOT NULL, Default `'private'`, Check `kind in ('private','shared')`.
- `owner_user_id` `String`, NULL, FK `users.id` — gesetzt für `private`, NULL für `shared`.

Zusätzlich:

- **Partieller Unique-Index** `uq_workspaces_one_shared` auf `(kind)` `WHERE kind='shared'` → erzwingt DB-seitig **genau einen** gemeinsamen Workspace.
- **Unique** `(owner_user_id)` `WHERE kind='private'` → höchstens ein Privat-Workspace pro User.

Begründung: Die Invariante „genau ein gemeinsamer Bereich, ein Privatbereich pro User" wird in der DB erzwungen, nicht nur im Service — passend zur bestehenden Invariant-Registry-Philosophie.

Migration additiv, keine Downgrade-Risiken der Klasse C/D. Bestehende Default-Workspaces sind im Upgrade auf `kind='shared'` **oder** `kind='private'` zu klassifizieren (Data-Migration-Schritt, siehe §10).

---

## 6. API-Design

Neuer Router `users` (Prefix `/api/v1/users`) und Ergänzung im `admin`-Kontext. Alle Endpunkte **admin-only** (Rolle `admin` im gemeinsamen Workspace), Fehler über das bestehende Error-Envelope `{"error":{"code","message","details"}}`.

### 6.1 User anlegen
`POST /api/v1/users`
Request:
```json
{ "display_name": "Vorname Nachname", "login": "user@telekom.de", "initial_password": "…" }
```
Ablauf (transaktional, ein Advisory-Lock-Scope `user_provisioning`):
1. Login-Eindeutigkeit prüfen.
2. `users`-Zeile anlegen (`is_active=true`, `password_hash=hash_password(...)`).
3. Privat-Workspace `kind='private', owner_user_id=<user>` anlegen; Membership `owner`.
4. Membership `member` im gemeinsamen Workspace anlegen.
Response `201`:
```json
{ "user_id":"…", "login":"…", "private_workspace_id":"…", "shared_workspace_id":"…" }
```

### 6.2 User auflisten / lesen
`GET /api/v1/users` (paginiert), `GET /api/v1/users/{user_id}`.

### 6.3 User deaktivieren
`POST /api/v1/users/{user_id}/deactivate` → `is_active=false`, aktive Sessions invalidieren.

### 6.4 Rolle im gemeinsamen Workspace setzen
`PUT /api/v1/users/{user_id}/shared-role` Body `{ "role": "admin" | "member" }`.

### 6.5 Gemeinsamen Workspace initialisieren (einmalig)
`POST /api/v1/admin/shared-workspace` → legt den gemeinsamen Workspace an, falls nicht vorhanden (idempotent, durch partiellen Unique-Index abgesichert).

### 6.6 Neue Fehlercodes (Ergänzung `app/core/errors.py`)

| Code | HTTP | Bedeutung |
|---|---|---|
| `USER_ALREADY_EXISTS` | 409 | Login bereits vergeben |
| `USER_NOT_FOUND` | 404 | unbekannte `user_id` |
| `SHARED_WORKSPACE_MISSING` | 409 | gemeinsamer Workspace nicht initialisiert |
| `SHARED_WORKSPACE_EXISTS` | 409 | zweite Initialisierung versucht |
| `LAST_ADMIN_PROTECTED` | 409 | letzten Admin im gemeinsamen Workspace degradieren verboten |
| `PASSWORD_POLICY_VIOLATED` | 422 | Initialpasswort erfüllt Policy nicht |

Wiederverwendet: `AUTH_REQUIRED`, `ADMIN_REQUIRED`, `REQUEST_VALIDATION_FAILED`, `WORKSPACE_ACCESS_FORBIDDEN`.

---

## 7. Service- und Repository-Schicht

- `ProvisioningService` (neu): `create_user`, `deactivate_user`, `set_shared_role`, `ensure_shared_workspace`. Kapselt die transaktionale Mehrschritt-Logik; nutzt Advisory-Lock (`user_provisioning`) analog zu bestehenden Lock-Scopes.
- `UserRepository` / `WorkspaceRepository` (neu oder Erweiterung `repositories/documents.py`): reine DB-Zugriffe, keine Businessregel im Router.
- `AuthService` bleibt unverändert; `create_user` nutzt dessen `hash_password`.
- Router `users.py`: nur HTTP-Mapping + Dependency-Injection, keine direkte DB-Nutzung.

---

## 8. Sicherheit und Isolation

- Provisioning-Endpunkte: Dependency `require_admin` (Rolle `admin` im gemeinsamen Workspace).
- Kein Endpoint akzeptiert `user_id`/`workspace_id` als Identitätsquelle aus Query/Body.
- Passwort-Policy als eigener Validator (Mindestlänge etc. — Werte sind PO-Entscheidung, §11).
- Deaktivierung invalidiert `auth_sessions` des Users (Token-Hash-Löschung).
- Privat-Workspace ist **nur** für seinen `owner` sichtbar; Prüfung über `require_workspace_member` + `kind`/`owner_user_id`.
- Schutzregel `LAST_ADMIN_PROTECTED`: der gemeinsame Workspace muss stets ≥1 aktiven Admin haben.

---

## 9. Audit-Trail

Neue Audit-Events (bestehendes Audit-Schema): `USER_CREATED`, `USER_DEACTIVATED`, `SHARED_ROLE_CHANGED`, `SHARED_WORKSPACE_INITIALIZED`. Felder: `actor` (Admin-Login), `subject` (betroffener User), `workspace_id`, Zeitstempel, Korrelation-ID.

---

## 10. Migration und Rollout

1. Additive Migration `00xx_workspaces_kind_owner`: Felder `kind`, `owner_user_id`, partielle Unique-Indizes.
2. Data-Migration: bestehenden Default-Workspace klassifizieren. **Entscheidung nötig** (§11): wird der heutige Default-Workspace zum gemeinsamen Bereich, oder zum Privatbereich des Default-Users?
3. `seed_auth.py` erweitern/ablösen: aus dem Single-User-Seed wird „Bootstrap-Admin + gemeinsamer Workspace"; weitere User nur noch über die API.
4. Kein Hard-Cut: alter Seed bleibt bis Bootstrap-Admin verifiziert lauffähig.

---

## 11. Offene Entscheidungen (PO)

1. **Klassifizierung des heutigen Default-Workspace:** gemeinsamer Bereich oder Privatbereich des Bootstrap-Admins?
2. **Schreibrechte im gemeinsamen Bereich** (Detail in Block 2): dürfen alle `member` schreiben, oder nur `admin`? Default-Annahme dieses Konzepts: `member` = lesen + Dokumente hinzufügen, `admin` = zusätzlich löschen/archivieren.
3. **Passwort-Policy:** Mindestlänge, Komplexität, Ablauf — konkrete Werte.
4. **Anlage-Modell:** ausschließlich Admin legt User an (angenommen), oder später Self-Service mit Einladung?

---

## 12. Teststrategie (Truth-Marker `m4a_auth_truth`)

- **Unit:** `ProvisioningService` — Erfolg, Login-Kollision, letzter-Admin-Schutz, Deaktivierung invalidiert Session.
- **API:** alle Endpunkte inkl. Fehlercodes und Admin-Guard (`ADMIN_REQUIRED`).
- **PostgreSQL-Integration (gegen echte DB, SCGB-01):**
  - Anlegen eines Users erzeugt genau 1 Privat-Workspace + 1 gemeinsame Membership.
  - Partielle Unique-Indizes verhindern zweiten gemeinsamen Workspace / zweiten Privatbereich.
  - Isolationstest: User A sieht Privat-Workspace von User B **nicht** über Read/Search/Chat/Retrieval; gemeinsamen Bereich sehen beide.
- Nachweis ausschließlich über aktuellen Report unter `reports/current/`, nicht über statische Zähler.

---

## 13. Abnahmekriterien (Definition of Done, Block 1)

- [ ] Additive Migration angewandt (`kind`, `owner_user_id`, partielle Unique-Indizes) — `alembic upgrade head` rc=0 gegen echte DB.
- [ ] Admin kann via API User anlegen; Privat-Workspace + gemeinsame Membership entstehen automatisch.
- [ ] DB erzwingt: genau ein gemeinsamer Workspace, höchstens ein Privatbereich pro User.
- [ ] Deaktivierter User kann sich nicht anmelden; Sessions invalidiert.
- [ ] Isolationstest privat/fremd/gemeinsam grün gegen echte PostgreSQL.
- [ ] Kein produktiver Pfad nutzt Default-User/Default-Workspace.
- [ ] Audit-Events vorhanden und geprüft.
- [ ] `m4a_auth_truth`-Report unter `reports/current/` grün (fehlerfreier Live-Lauf).

---

## 14. Umsetzungsschnitte (Stories)

1. **DB:** Migration `kind`/`owner_user_id` + partielle Unique-Indizes + Data-Migration Default-Workspace.
2. **Fehlercodes:** neue `ApiError`-Klassen (§6.6).
3. **Repository:** `UserRepository`/`WorkspaceRepository`.
4. **Service:** `ProvisioningService` mit Advisory-Lock, transaktional.
5. **Router:** `users.py` + `require_admin`-Dependency; Registrierung in `api/v1/router.py`.
6. **Bootstrap:** `seed_auth.py` → Bootstrap-Admin + gemeinsamer Workspace.
7. **Tests:** Unit + API + PostgreSQL-Integration inkl. Isolationstest (`m4a_auth_truth`).
8. **Doku:** API-Vertrag + Known-Limitations aktualisieren.

Abhängigkeit: Story 1 blockiert 3–7. Block 2 (Schreibregeln gemeinsamer Bereich) setzt auf 1–5 auf.
