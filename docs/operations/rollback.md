# Rollback-Prozedur — Ruflo

Stand: 2026-06-17

---

## Wann Rollback?

- Backend-Fehlerrate > 10% nach Deployment
- Kritischer Datenverlust festgestellt
- Health-Check schlägt fehl
- PO-Entscheidung

---

## Code-Rollback

```bash
# Aktuellen Tag identifizieren
git tag -l | sort -V | tail -5

# Zurückrollen
git checkout <previous-tag>

# Backend neu starten
```

---

## DB-Rollback (Alembic)

```bash
# Eine Migration zurück
alembic downgrade -1

# Auf bestimmte Version
alembic downgrade <revision>

# Aktuellen Stand prüfen
alembic current
```

**Vorsicht:** Downgrade kann Datenverlust verursachen bei nicht-reversiblen Migrationen. Backup vorher prüfen.

---

## Restore aus Backup

Wenn Code- und DB-Rollback nicht ausreicht:

```bash
pg_restore -d $DATABASE_URL backup_db_<timestamp>.dump
tar -xzf backup_uploads_<timestamp>.tar.gz -C uploads/
python scripts/validate_restore.py
```

Vollständige Prozedur: `docs/operations/operations_manual.md` Abschnitt 6.

---

## Entscheidungsbaum

```
Deployment-Fehler
  │
  ├── Health-Check OK?
  │     └── Nein → Code-Rollback (git checkout)
  │
  ├── DB-Schema korrekt?
  │     └── Nein → alembic downgrade -1
  │
  └── Datenverlust?
        └── Ja → Restore aus Backup
```

---

## Kommunikation

Bei produktivem Rollback:
1. PO informieren
2. Fehlerursache dokumentieren
3. Incident-Ticket anlegen
4. Post-Mortem nach Behebung
