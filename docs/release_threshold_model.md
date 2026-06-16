# Release Threshold Model — Ruflo V1

**Status:** AKTIV  
**Erstellt:** 2026-06-16  
**Gilt ab:** Produktreife-Assessment V2

---

## Schwellwerte

| Stufe | Produktreife-Score | Bedeutung |
|-------|--------------------|-----------|
| RC (Release Candidate) | >= 80 | Für eingeschränkten externen Test freigegeben |
| GA (General Availability / 1.0) | >= 85 | Vollständige Produktionsfreigabe |

---

## RC — Freigabebedingungen (alle müssen erfüllt sein)

1. **Produktreife-Score >= 80**
2. **Keine BLOCKING_SECURITY-Befunde** — Sicherheitslücken mit kritischer oder hoher Einstufung blockieren RC ohne Ausnahme
3. **Sichtbare technische IDs = 0** — `ui_technical_id_leak_audit.json` muss `leaks: 0` aufweisen
4. **Gold Path >= 7/8 PASS** — maximal 1 fehlender Schritt erlaubt, wenn dieser nicht sicherheits- oder datenverlustkritisch ist
5. **CONDITIONAL_PASS erlaubt** — einzelne Gates können bedingt bestanden sein, sofern die bekannten Einschränkungen dokumentiert sind

### RC — was explizit erlaubt ist

- Fehlende Features aus dem `Not-in-Scope` der `version_1_0_scope_freeze.md`
- CONDITIONAL_PASS auf nicht-kritischen Gates (z.B. Dashboard W06 Drift)
- 1 Gold-Path-Schritt FAIL, wenn keine Sicherheits- oder Datenverlustrisiken
- Offen: Lazy Loading, KWIC-Highlighting, deutsches FTS-Stemming (P2/P3)

---

## GA — Freigabebedingungen (alle müssen erfüllt sein)

1. **Produktreife-Score >= 85**
2. **Gold Path 8/8 PASS** — vollständiger Durchlauf ohne manuellen Eingriff, keine technischen IDs als Primärwert
3. **Keine kritischen Blocker in UX, Security oder Data Loss**
4. **documentation_truth_lint PASS** — keine veralteten oder widersprüchlichen Spezifikationen
5. **Nur PASS oder BLOCKED** — CONDITIONAL_PASS ist für GA nicht zulässig

### GA — Entscheidungsmatrix

| Bedingung | Wert | GA-Entscheidung |
|-----------|------|-----------------|
| Score >= 85 | Ja | Weitermachen |
| Score >= 85 | Nein | BLOCKED |
| Gold Path 8/8 | Ja | Weitermachen |
| Gold Path < 8/8 | Nein | BLOCKED |
| Kritischer Blocker | Ja | BLOCKED (immer) |
| Alle PASS | Ja | GA_ALLOWED |
| CONDITIONAL_PASS vorhanden | Ja | BLOCKED (GA kennt kein Conditional) |

---

## Klassifikation sicherheits- und datenverlustkritischer Schritte

Diese Schritte sind RC-ausschlussfähig wenn sie FAIL sind:

| Gold-Path-Schritt | Kritisch für RC? | Begründung |
|-------------------|------------------|------------|
| GP-01 Login | Ja — Security | Authentifizierung |
| GP-02 Dokument importieren | Nein | Datenverlust nur bei Crash, nicht bei FAIL |
| GP-03 Dokument anzeigen | Nein | UX-Qualität, kein Security/Loss |
| GP-04 Thema finden | Nein | Feature nicht implementiert, kein Datenverlust |
| GP-05 Analyse starten | Nein | Feature nicht implementiert, kein Datenverlust |
| GP-06 Analyse freigeben | Ja — Datenverlust | Approval-Mechanismus; FAIL = kein Freigabeprozess |
| GP-07 Export erzeugen | Nein | Feature nicht implementiert, kein Datenverlust |
| GP-08 Logout | Ja — Security | Session-Invalidierung |

**Folgerung:** GP-01, GP-06, GP-08 blockieren RC bei FAIL. Die anderen 5 Schritte erlauben maximal 1 FAIL für RC (CONDITIONAL_RC).

---

## CONDITIONAL_PASS — Definition

- Gilt ausschließlich für RC, nicht für GA
- Voraussetzung: bekannte Einschränkungen müssen in `reports/current/known_limitations.json` dokumentiert sein
- Kein CONDITIONAL_PASS bei Security- oder Datenverlustkritischen Gates
- PO muss CONDITIONAL_PASS explizit bestätigen

---

## Entscheidungstypen

| Status | Bedeutung |
|--------|-----------|
| `RC_ALLOWED` | Alle RC-Bedingungen erfüllt, Score >= 80 |
| `CONDITIONAL_RC` | RC möglich mit dokumentierten Einschränkungen, Score >= 80 |
| `GA_ALLOWED` | Alle GA-Bedingungen erfüllt, Score >= 85 |
| `BLOCKED` | Mindestens eine Pflichtbedingung nicht erfüllt |

---

## Gültigkeitsbereich

- Dieses Modell gilt für Ruflo V1.0 und folgende Minor-Releases bis V2.0
- Schwellwerte können durch PO-Entscheidung angepasst werden (mit Dokumentation in diesem Dokument)
- Sicherheits-Constraints PROHIBIT-02, -06, -08 sind unabhängig von Schwellwerten und niemals verhandelbar
