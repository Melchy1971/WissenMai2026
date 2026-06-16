# Glossary

## Acronyms & Terms

| Term | Meaning |
|------|---------|
| PO | Product Owner |
| SAP | Enterprise ERP system used at Telekom |
| myWiki | Telekom internal wiki/documentation platform |
| M3a, M4, M5, M5a, M5b | Frühere Milestones (abgeschlossen). Projekt heißt jetzt Ruflo. |
| RC | Release Candidate |
| ADR | Architecture Decision Record |
| Gate | Quality gate — project must pass before advancing |
| NO_GO | Gate failed, milestone blocked |
| GO | Gate passed |
| Ruflo | Interner Produktname für Wissensbasis V1 (FastAPI + React + PostgreSQL) |
| P1-GAP-01 | Tags ORM-Models fehlen (Category, Tag, DocumentTag) |
| P1-GAP-02 | Tags API-Endpunkte fehlen (POST /tags, POST /documents/:id/tags) |
| AGAP-02 | Analysis Gap: POST /analysis/jobs/:id/cancel fehlt |
| AGAP-07 | Analysis Gap: AnalysisPage.jsx nicht implementiert |
| RCB-001 | NAV-Link /search vs /chat — potenziell fehlende Verlinkung zur Suchseite |
| DC-F01 | Befund: UUIDs (id, workspaceId, ownerUserId) in DocumentMetaCard sichtbar |
| Gold Path | 8-Schritt End-to-End-Szenario: Login → Import → Dok anzeigen → Thema → Analyse → Freigabe → Export → Logout |
| Scope Freeze | Fixierter Funktionsumfang für 1.0 — neue Features kommen frühestens in 1.1 |
| PROHIBIT-02 | Sicherheitsregel: Kein RepairButton in irgendeiner Komponente |
| PROHIBIT-06 | Sicherheitsregel: Kein CleanupButton in irgendeiner Komponente |
| PROHIBIT-08 | Sicherheitsregel: Keine automatische M5c-Ausführung ohne PO-Approval |
| M5c | Cleanup-Phase — NO_GO bis m5c_start_gate = PASS und PO-Sign-off |
| Produktreife-Score | Gewichteter Score 0–100 (Fachlich 40%, UX 25%, Betrieb 15%, Release 20%). Schwellwert: 85 für 1.0 |
| TEILWEISE | Feature-Status: Kern implementiert, Teile fehlen |
| NICHT_IMPLEMENTIERT | Feature-Status: vollständig fehlend |
| VOLLSTÄNDIG | Feature-Status: vollständig und produktionsreif |
| CONDITIONAL_PASS | Gate-Status: bedingt bestanden, bekannte Einschränkungen vorhanden |

## Workplace Shorthand

*(Add as discovered in conversation)*
