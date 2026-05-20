# Documentation Release Audit

Stand: 2026-05-20T10:22:10+02:00

## Umfang

Geprueft:

- `masterplan.md`
- `docs/status.md`
- `docs/frontend.md`
- `docs/api.md`
- `docs/security.md`
- `docs/operations.md`
- `docs/changelog.md`
- `docs/known_limitations.md`

## Verwendete Gate-Artefakte

- `reports/m3a_release_candidate.json`: `gate_passed`, `GO`
- `reports/m4_release_candidate.json`: `tested`, `NO_GO`
- `reports/postgres_truth_report.json`: `138 collected`, `120 passed`, `16 failed`, `2 errors`, `exit_code = 1`
- `docs/known_limitations.json`: 15 bekannte Limitations

## Findings

| ID | Schwere | Datei | Befund | Fix |
|---|---|---|---|---|
| DRA-001 | critical | `docs/security.md:7`, `docs/security.md:119` | M4a wird als aktuell freigabefaehig bzw. abgeschlossen dargestellt, obwohl M4 RC `NO_GO` ist und `reports/m4a_auth_truth_report.json` fehlt. | M4a nur als Teilbefund dokumentieren; Abschluss nur mit M4a-Splitreport und M4 Gesamtgate PASS. |
| DRA-002 | critical | `docs/security.md:81` | Lifecycle-Mutationen werden mit gruenem Truth-/Transition-Nachweis als nicht mehr offener M4-Blocker beschrieben. | Aussage auf vorhandenen Slice begrenzen und M4-Blockerstatus aus `reports/m4_release_candidate.json` uebernehmen. |
| DRA-003 | critical | `masterplan.md:1251`, `masterplan.md:1252`, `masterplan.md:1253`, `masterplan.md:1396`, `masterplan.md:1399` | Masterplan enthaelt aktuelle oder nicht ausreichend historisierte gruene M4-Aussagen zu Truth-Gate, M4a/b/c und `postgres_truth`. | Als historische Sprintziele markieren oder in Startbedingungen umformulieren; aktuelle Bewertung auf M4 RC `NO_GO` verweisen. |
| DRA-004 | high | `docs/security.md:21`, `docs/security.md:22`, `docs/security.md:23`, `docs/security.md:109`, `docs/security.md:110`, `docs/security.md:111` | Offene Auth-/Session-/CSRF-/Lifecycle-Limitations sind nicht als eigener Known-Limitation-Eintrag klassifiziert. | M4a-Security/Auth-Produktflow im Register eintragen oder als non-blocking/deferred klassifizieren. |
| DRA-005 | medium | `docs/changelog.md` | Historische `passed`-Zahlen stehen teils ohne direkte Reportpfad-Referenz. | Reportpfad, Datum und historische Einordnung nachtragen. |
| DRA-006 | medium | `docs/status.md:16`, `docs/status.md:94`, `docs/status.md:159`, `docs/status.md:849` | Aeltere Abschlussaussagen sind nicht durchgaengig auf das neue RC-/Gate-Modell abgebildet. | Mit Gate-Artefakt verknuepfen oder als historischer Vor-RC-Stand markieren. |

## Fixliste

| ID | Prioritaet | Dateien | Aktion | Blockiert Freigabe |
|---|---|---|---|---|
| FIX-001 | P0 | `docs/security.md` | M4a-Freigabe- und Abschlussaussagen entfernen oder an `m4a_auth_truth_report.json` plus M4 Gesamtgate PASS binden. | ja |
| FIX-002 | P0 | `masterplan.md` | Aktuelle gruene M4-Aussagen korrigieren und auf `reports/m4_release_candidate.json` sowie `reports/postgres_truth_report.json` verweisen. | ja |
| FIX-003 | P1 | `docs/known_limitations.md`, `docs/known_limitations.json` | Expliziten M4a-Security/Auth-Produktflow-Eintrag fuer Session, Logout, CSRF und Lifecycle-Hardening anlegen oder als non-blocking/deferred klassifizieren. | ja |
| FIX-004 | P2 | `docs/changelog.md`, `docs/status.md` | Historische `passed`-Zahlen und Abschlussaussagen mit Reportpfaden oder historisch/ueberholt-Markierung versehen. | nein |

## Freigabe

Nein.

Die Dokumentation ist fuer eine Release-Freigabe noch nicht konsistent, weil kritische M4-Freigabe- und gruen-Aussagen nicht durch die aktuellen Gate-Artefakte gedeckt sind. Massgeblich ist derzeit `reports/m4_release_candidate.json` mit `NO_GO`.
