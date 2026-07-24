# Story 1 — Migration: Umsetzungsnotiz

Stand: 2026-07-24. Status: **implementiert + gegen echtes PostgreSQL 16 verifiziert.** Nicht committet.

## Geänderte Dateien (im Repo)

- `backend/migrations/versions/20260724_0027_workspaces_kind_owner.py` (neu) — Revision `20260724_0027`, revidiert `20260618_0026` (bisheriger Head).
- `backend/app/models/documents.py` — `Workspace` um `kind` und `owner_user_id` ergänzt (additiv).

## Designentscheidung (bestätigt am Code)

Der bereits vorhandene partielle Unique-Index `ux_workspaces_single_default` (`UNIQUE (is_default) WHERE is_default`) erzwingt schon „genau ein Default-Workspace". Die Migration nutzt genau diesen Mechanismus als Singleton für den **gemeinsamen Bereich** — kein zweiter, konkurrierender Mechanismus. Verknüpft über den Consistency-Check `(kind='shared') <=> (is_default=true)`.

PO-Entscheidung eingebaut: heutiger Default-Workspace → `kind='shared'` (bestehende Dokumente werden gemeinsam).

## Verifikation gegen echtes Postgres (fehlerfreier Live-Lauf)

| Test | Erwartung | Ergebnis |
|---|---|---|
| `upgrade 0026 -> 0027` | läuft | PASS |
| Backfill Default-Workspace | `kind='shared'`, `owner_user_id=NULL` | PASS |
| Legacy-Private einfügen (`kind='private'`, owner gesetzt) | erlaubt | PASS |
| Zweiter Private mit gleichem Owner | **verweigert** (uq_workspaces_owner_private) | PASS |
| Zweiter Shared (`is_default=true`) | **verweigert** (ux_workspaces_single_default) | PASS |
| Inkonsistenz `shared` + `is_default=false` | **verweigert** (ck_workspaces_kind_default_consistency) | PASS |
| Ungültiges `kind='team'` | **verweigert** (ck_workspaces_kind_allowed) | PASS |
| `downgrade -1` → Spalten weg → `upgrade head` → Spalten zurück | idempotent | PASS |
| Modell auf SQLite (`create_all` + Insert) | Unit-Basis unversehrt | PASS |

## Bekannte Entscheidungen / Grenzen

- Legacy-Private-Workspaces ohne auflösbaren Owner behalten `owner_user_id=NULL`. Die Invariante „private muss Owner haben" wird für **neue** Workspaces im `ProvisioningService` (spätere Story) erzwungen, nicht per harter DB-Check auf Altbestand. Bewusst, um die Migration nicht an Altdaten scheitern zu lassen.
- Die strengen Checks liegen in der PG-Migration, **nicht** im ORM-`table_args`. Grund: die breite SQLite-Unit-Suite erzeugt Tabellen über `create_all`; ein Consistency-Check im Modell würde bestehende Tests brechen, die `Workspace(is_default=True)` ohne `kind` anlegen. Auf der echten DB (PG) gilt der Check voll.

## Test-Snippet für CI (in `backend/tests/integration/test_migrations.py`, Marker `@pytest.mark.postgres`)

```python
def test_workspaces_kind_owner_constraints(test_database_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", test_database_url)
    _upgrade_to("head")
    with psycopg.connect(psycopg_url(test_database_url)) as conn:
        cur = conn.cursor()
        # Backfill: default workspace is shared
        cur.execute("SELECT kind FROM workspaces WHERE is_default = true")
        assert cur.fetchone()[0] == "shared"
        # invalid kind rejected
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute("INSERT INTO workspaces (id,name,is_default,kind,created_at) "
                        "VALUES ('x','X',false,'team',now())")
        conn.rollback()
```

## Nächster Schritt

Story 2 (neue Fehlercodes) + Story 3/4 (`UserRepository`/`WorkspaceRepository`, `ProvisioningService`). Migration und Modell sind die Grundlage; die Provisioning-Logik setzt darauf auf.
