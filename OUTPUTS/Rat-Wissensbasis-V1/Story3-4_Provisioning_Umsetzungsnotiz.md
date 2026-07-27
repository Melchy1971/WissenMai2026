# Story 3/4 — Provisioning: Umsetzungsnotiz

Stand: 2026-07-24. Status: **implementiert + standalone gegen SQLite verifiziert (8/8 Szenarien).** Nicht committet.

## Geänderte / neue Dateien (im Repo)

- `backend/app/services/advisory_lock.py` — Scope `user_provisioning` (ID 6) + `acquire_user_provisioning_lock`.
- `backend/app/repositories/provisioning.py` (neu) — `UserRepository`, `WorkspaceRepository` (inkl. Memberships, `count_active_admins`).
- `backend/app/services/provisioning.py` (neu) — `ProvisioningService`.
- `backend/tests/test_provisioning_service.py` (neu) — 11 Tests, Marker `m4a_auth_truth`.

## ProvisioningService — Verhalten

- `ensure_shared_workspace()` idempotent; `initialize_shared_workspace()` wirft `SHARED_WORKSPACE_EXISTS`.
- `create_user()` transaktional (ein Commit), auf PostgreSQL per Advisory-Lock (`user_provisioning`) pro Login serialisiert: legt User an, erzeugt Privat-Workspace (`kind='private'`, `owner_user_id`), Membership `owner` (privat) + `member` (gemeinsam). Passwort via bestehendem `hash_password` (PBKDF2, zufälliger Salt).
- `deactivate_user()` setzt `is_active=false` und widerruft alle offenen Sessions (`revoked_at`).
- `set_shared_role()` schützt den letzten aktiven Admin (`LAST_ADMIN_PROTECTED`).
- Passwort-Policy: Mindestlänge 8 als sicherer Default; konkrete Werte bleiben PO-Entscheidung (Fachkonzept §11.3).

## Standalone-Verifikation gegen SQLite (8/8)

| Szenario | Ergebnis |
|---|---|
| create_user ohne Shared → `SHARED_WORKSPACE_MISSING` | PASS |
| ensure_shared_workspace → `kind='shared'`, `is_default=true` | PASS |
| create_user → Privat (`kind='private'`, owner) + Memberships `owner`/`member` | PASS |
| doppelter Login → `USER_ALREADY_EXISTS` | PASS |
| schwaches Passwort → `PASSWORD_POLICY_VIOLATED` | PASS |
| echte `AuthService.login` mit neuem User | PASS |
| letzten Admin degradieren → `LAST_ADMIN_PROTECTED`; mit 2 Admins erlaubt | PASS |
| deaktivierter User kann sich nicht mehr anmelden | PASS |

Verifiziert per Standalone-Skript (importiert nur die Dokument-Modelle + Services), nicht über den pytest-Gate — Grund siehe unten.

## Vorbefund BEHOBEN — tags/categories ORM-Modelle ergänzt

Update 2026-07-24: Der unten beschriebene Defekt ist **behoben**. In `app/models/documents.py` sind jetzt die fehlenden ORM-Modelle `Category`, `Tag`, `DocumentTag` (exakt nach Migration `20260430_0003`) ergänzt. Ergebnis:

- `create_all` mit importiertem `app.main`: **OK** (32 Tabellen, `tags` registriert) — der SQLite-Unit-Pfad ist wieder funktionsfähig.
- `tests/test_provisioning_service.py`: **11 passed** durch den echten pytest-Harness (Marker `m4a_auth_truth` akzeptiert).
- Regression `tests/test_documents_read_api.py`: **26 passed** — die Modelländerung bricht bestehende Tests nicht.

### Ursprünglicher Defekt (zur Dokumentation)

- `app/models/topics.py` (`topic_tags`) hat einen Fremdschlüssel `tag_id → tags.id`.
- Es existiert **kein ORM-Modell** für die Tabelle `tags` (auch nicht für `categories`); beide gibt es nur als Migration `20260430_0003_categories_tags.py`.
- `tests/conftest.py` importiert auf Modulebene `from app.main import app` → registriert `topic_tags` → `Base.metadata.create_all` scheitert mit:

  `NoReferencedTableError: Foreign key 'topic_tags.tag_id' could not find table 'tags'`

Reproduktion (ohne meine Dateien):
```python
import app.main
from app.models.documents import Base
from sqlalchemy import create_engine
Base.metadata.create_all(create_engine("sqlite://"))  # -> NoReferencedTableError
```

Konsequenz: Der gesamte SQLite-Unit-Pfad ist betroffen, sobald `app.main` importiert wird. Das ist dieselbe Code-vs-Truth-Drift, die sich durch das ganze Projekt zieht. **Fix (separate, kleine Story):** ORM-Modelle `Tag` und `Category` passend zur Migration `0003` ergänzen. Danach läuft `tests/test_provisioning_service.py` grün — die Datei ist bereits korrekt und CI-fertig (Marker `m4a_auth_truth`).

## Offen / nächste Schritte

- Vorbefund `tags`/`categories`-ORM-Modelle nachziehen (entblockt den Unit-Pfad).
- Story 5: Router `users.py` + `require_admin`-Dependency, Registrierung in `api/v1/router.py`.
- Story 6: `seed_auth.py` → Bootstrap-Admin + gemeinsamer Workspace.
