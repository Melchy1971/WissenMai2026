## Ziel

## Geaenderte Bereiche

## Tests

## Risiken

## GUI-Governance (falls GUI betroffen)

- Runtime-State fuer den betroffenen Slice:
- Error-/Recovery-Verhalten:
- Drift-/Degraded-Sichtbarkeit:
- Workspace-/Security-Kontext:
- Truth-/Gate-Nachweis:

## Checkliste

- [ ] Kein Auth-Code in V1 eingefuehrt
- [ ] Schemaaenderung hat Alembic-Migration
- [ ] Dokumentbezug bleibt zitierfaehig
- [ ] Akzeptanzkriterien erfuellt
- [ ] GUI-Slice respektiert Runtime-State-Machine, Error-Catalog und Cache-Governance
- [ ] Kein Fake-Green, kein versteckter Fallback, kein Empty-State bei technischem Fehler
- [ ] Workspace-Isolation, Request-Ticketing und zentrale API-Abstraktionen bleiben intakt
- [ ] GUI-Regressionen sind bewertet; Truth-/Gate-Status wird nicht durch lokale Gruenlaeufe ueberstimmt
