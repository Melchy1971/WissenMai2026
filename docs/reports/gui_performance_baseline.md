# GUI Performance Baseline

Stand: 2026-06-12

## Baseline

| Bereich | Umsetzung |
|---|---|
| Dashboard Initial Load | V3 Summary und Activity werden parallel geladen. |
| Settings Load | Ein GET, sections lokal gerendert, PATCH nur Diff. |
| Chat Streaming | Requests laufen ueber zentralen API Client mit AbortController. |
| Audit Log 1000 Eintraege | API-Limit vorgesehen; generische grosse Listen nutzen VirtualizedTable. |
| RAG Documents 1000 Dokumente | Empty/Loading/Error State vorhanden; Tabellen koennen auf VirtualizedTable umgestellt werden. |
| Memory Table 1000 Memories | `SimpleListPage` nutzt `VirtualizedTable`. |
| Agent Execution View 100 Steps | Agent Runs werden ueber Orchestrator Events angezeigt; grosse Listen sind virtualisierbar. |

## Technische Controls

- `AbortController` im zentralen API Client.
- Debounce in Suche vorhanden.
- `VirtualizedTable` fuer grosse generische Listen.
- Pagination-faehige API-Contracts mit `items`/`total`.

## Offen

RAG-, Audit- und dedizierte Data-Quality-Tabellen sollten im naechsten Schritt ebenfalls auf `VirtualizedTable` migriert werden, sobald die API echte 1000er-Responses liefert.
