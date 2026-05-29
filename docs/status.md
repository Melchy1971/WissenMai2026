# Projektstatus

Der aktuelle Projektstatus wird ausschliesslich aus `reports/current/masterplan_status.json` abgeleitet. Der lesbare maschinelle Statusabschnitt steht in `docs/generated/status_section.md`.

## Boundary M3a/M4/M5

- M3a: `reports/current/m3a_release_candidate.json`; Backend-M4- oder M5-Reports duerfen M3a nicht blockieren.
- M4: `reports/current/m4_backend_release_candidate.json`; Split-Reports bleiben Eingaben dieses Release Candidate.
- M5 Vorbereitung: nur erlaubt, wenn M4 Backend RC PASS ist.
- M5 Implementierung: bleibt `NO_GO` bis ein expliziter M4e/Operations-Release-Report vorliegt.

## Dokumentationsregel

Manuelle Status-, PASS-, GO-, Prozent- oder Abschlussaussagen sind in diesem Dokument nicht zulaessig. Bei Statusaenderungen zuerst Reports unter `reports/current/` erneuern, danach `scripts/generate_masterplan_status_v3.py` und `scripts/validate_documentation_truth.py` ausfuehren.
