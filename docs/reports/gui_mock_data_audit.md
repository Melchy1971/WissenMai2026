# GUI Mock Data Audit

Stand: 2026-06-12

## Ergebnis

Produktive GUI-Routen rendern keine harten finalen Beispielwerte fuer Tools, Memory, Tasks, Projects, Agents, Collaboration, Governance, Settings, RAG oder Dashboard. Produktive Listen starten mit API-Daten und zeigen Empty States, wenn die API keine Items liefert.

## Umgesetzte Korrekturen

- RAG GUI Backend: harte Beispiel-Dokumente entfernt.
- Agent GUI Backend: harte Beispiel-Agenten entfernt.
- Document Center: Mock-Kommentar entfernt; Filter werden aus API-Daten abgeleitet.
- Fehlende Center-Routen verwenden API-Client, Loading State, Error State und Empty State.
- Mocks bleiben in Tests/Testfixtures erlaubt.

## Resthinweis

Untracked `backend/app/services/analysis/stubs.py` war bereits im Worktree vorhanden und wurde nicht angefasst. Dieser Stub gehoert nicht zu den produktiven GUI-Seiten, muss aber vor Release separat klassifiziert werden.

