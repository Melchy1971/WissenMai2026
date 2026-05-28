# Governance-stabiler Entwicklungsmodus

Stand: 2026-05-20

## Ziel

Nach M3a/M4 darf Entwicklung nicht wieder in einen feature-getriebenen Modus zurueckfallen. Status, Fortschritt und Freigabe entstehen aus Artefakten, nicht aus manuellen Aussagen oder Feature-Druck.

## Entwicklungsmodus

Der verbindliche Modus ist `governance_stable`.

Jede Arbeit beginnt mit:

- Scope und Ziel-Gate
- Testmarker-Zuordnung
- erwarteten Reports
- Release-Candidate-Bezug
- Known-Limitation-Auswirkung
- Documentation-Audit-Auswirkung
- Gate-Drift-Auswirkung
- Masterplan-Status-Auswirkung

Ohne diese Zuordnung bleibt Arbeit Analyse, Planung oder Blocker-Behebung. Sie ist keine Feature-Implementierung und darf keinen Abschlussclaim erzeugen.

## Prinzipien und Regeln

| ID | Prinzip | Regel | No-Go-Verhalten |
|---|---|---|---|
| GSDM-001 | Artefaktbasierte Wahrheit | Status kommt aus maschinenlesbaren Reports, RCs, Validatoren und Audits. | Fehlende oder widerspruechliche Artefakte ergeben `blocked`, `unknown` oder `not_verified`, nie `pass`. |
| GSDM-002 | Gate-spezifische Reports | Ein Gate wertet nur seinen eigenen Report und erlaubte Dependencies aus. | Keine Freigabe aus fremden Reports; M5/Governance blockiert M4 nicht. |
| GSDM-003 | Marker-disziplinierte Tests | Jeder Gate-Test hat genau einen Gate-Marker. | Unklassifizierte oder mehrdeutige Tests blockieren Taxonomie und Drift Detection. |
| GSDM-004 | Release Candidate Pflicht | Kein Meilenstein gilt ohne RC als abgeschlossen. | `implemented` oder `tested` ohne `truth_validated`/`gate_passed` ist offen. |
| GSDM-005 | Known Limitations Register | Jeder offene Blocker ist klassifiziert. | Unregistrierte Blocker stoppen Gate- und Release-Entscheidungen. |
| GSDM-006 | Documentation Audit Pflicht | Abschluss- und Release-Aussagen brauchen Doku-Audit. | Doku-Widersprueche oder alte Gruen-Zahlen blockieren Freigabe. |
| GSDM-007 | Gate Drift Detection | Drift wird vor Freigaben geprueft. | Drift `FAIL` blockiert Implementierungs- oder Release-Go fuer betroffene Gates. |
| GSDM-008 | Masterplan Status Engine | Masterplan-Status wird generiert. | Manuelle Statusaussagen duerfen `reports/current/masterplan_status.json` nicht ueberschreiben. |

## No-Go-Verhalten

| Situation | Verhalten |
|---|---|
| Artefakt fehlt | Status `unknown` oder `not_verified`; keine Freigabe. |
| Gate ist rot | Betroffener Scope bleibt `FAIL` oder `BLOCKED`. |
| Tests sind unklassifiziert | Taxonomie und Drift Detection schlagen fehl. |
| Blocker fehlt im Register | Entscheidung stoppt, bis Known Limitation erfasst ist. |
| Documentation Audit ist rot | Keine Release- oder Abschlussfreigabe. |
| Gate Drift ist rot | Keine Implementierungs- oder Releasefreigabe fuer betroffene Gates. |
| Manuelle Doku widerspricht Maschinenstatus | Maschinenstatus gewinnt; Doku wird korrigiert oder historisiert. |
| Feature-Druck entsteht | Feature wird in RC, Backlog oder Gate-Scope ueberfuehrt; keine Umgehung. |

## Erlaubte Arbeit bei blockiertem Status

- Root-Cause-Analyse
- Report-Generatoren und Validatoren verbessern
- Known Limitations aktualisieren
- Documentation-Audit-Fixes
- Gate-Blocker beheben
- nicht-invasive Planung innerhalb der Governance Boundary

## Verbotene Arbeit bei blockiertem Status

- neue Feature-Implementierung ohne Gate-Zuordnung
- Release-Claims ohne RC und Audit
- manuelle Gruen- oder Abschlussaussagen
- M5-Implementierung vor M5-Go
- M5/Governance-Findings als M4-Blocker verwenden
- alte Reports als aktuelle Wahrheit verwenden

## Verbindliche Artefakte

- `docs/governance-stable-development-mode.json`
- `docs/governance-boundary.json`
- `docs/release-candidate-model.json`
- `docs/known_limitations.json`
- `reports/current/documentation_truth_lint.json`
- `reports/current/gate_hierarchy_result.json`
- `reports/current/masterplan_status.json`
- `reports/current/recovery_sprint_gate.json`

Die maschinenlesbare Quelle fuer diesen Modus ist `docs/governance-stable-development-mode.json`.
