# Strategisches Zielbild Bewertungsmatrix

Stand: 2026-05-13

## Zweck

Diese Matrix ist das ausfuellbare Standard-Template fuer neue Features, mutierende Betriebsfunktionen und Architekturänderungen.

Sie prueft nicht primaer, ob eine Idee nuetzlich klingt, sondern ob sie zum strategischen Zielzustand des Systems passt.

Referenzen:

- `docs/strategic-target-state.md`
- `docs/strategic-target-state-review-guide.md`
- `docs/feature-governance-model.md`
- `docs/architecture-change-governance.md`
- `docs/operational-truth-governance.md`

---

## 1. Stammdaten

```text
Vorhaben:
Kurzbeschreibung:
Typ: Feature / Architekturänderung / Betriebsfunktion / Repair-Pfad / Admin-Aktion
Antragsteller:
Datum:
Betroffene Bereiche:
Vorläufige Risikoklasse: F1 / F2 / F3 / F4
```

## 2. Strategische Kernfrage

```text
Macht die Änderung das System langfristig verantwortbarer?

Antwort: ja / teilweise / nein
Begründung:
```

Wenn hier nicht mindestens `teilweise` mit belastbarer Begründung steht, ist das Vorhaben strategisch zurückzustellen oder abzulehnen.

---

## 3. Strategischer Fit

Für jeden Punkt bewerten:

- `stärkt`
- `neutral`
- `schwächt`
- `unklar`

und jeweils kurz begründen.

| Dimension | Bewertung | Begründung |
|---|---|---|
| Langfristige Konsistenz |  |  |
| Kontrollierbarkeit |  |  |
| Auditierbarkeit |  |  |
| Reparierbarkeit |  |  |
| Drift-Erkennung |  |  |
| Determinismus |  |  |
| Restore-Fähigkeit |  |  |
| Scope-Minimierung |  |  |
| Workspace-Isolation |  |  |
| Historische Nachvollziehbarkeit |  |  |

### Strategische Vorentscheidung

```text
Gesamtbewertung strategischer Fit: stark / ausreichend / schwach / nicht tragfähig
Begründung:
```

---

## 4. Systemprinzipien-Check

Jeder Punkt ist mit `ja`, `teilweise`, `nein` oder `nicht betroffen` zu beantworten.

| Frage | Antwort | Begründung |
|---|---|---|
| Bleibt die kanonische Wahrheit klar? |  |  |
| Bleiben abgeleitete Modelle rebuildbar? |  |  |
| Bleiben Zustandsübergänge explizit? |  |  |
| Ist der Eingriff minimal genug? |  |  |
| Ist das Verhalten idempotent oder abgesichert? |  |  |
| Bleibt historische Evidenz unangetastet? |  |  |
| Bleibt Restore als Designanforderung erhalten? |  |  |
| Bleibt das Verhalten reproduzierbar? |  |  |

---

## 5. Governance-Check

| Frage | Antwort | Begründung |
|---|---|---|
| Risikoklasse korrekt bestimmt? |  |  |
| Impact Assessment erforderlich und vorhanden? |  |  |
| Risk Matrix erforderlich und vorhanden? |  |  |
| Truth-Test-Plan erforderlich und vorhanden? |  |  |
| Rollback-Plan erforderlich und vorhanden? |  |  |
| Benötigt das Vorhaben ein neues oder erweitertes Gate? |  |  |
| Benötigt das Vorhaben neue Runbooks oder Governance-Dokumente? |  |  |

---

## 6. Betriebscheck

| Frage | Antwort | Begründung |
|---|---|---|
| Erzeugt die Änderung neue operative Last? |  |  |
| Erzeugt sie neue Queue-, Retry- oder Dead-Letter-Semantik? |  |  |
| Erzeugt sie neue Drift-Arten? |  |  |
| Erzeugt sie neue Cleanup- oder Retention-Relevanz? |  |  |
| Erfordert sie neue tägliche oder wöchentliche Checks? |  |  |
| Ist ein Dry-Run-first-Pfad nötig? |  |  |
| Ist vor Ausführung Backup-Verifikation Pflicht? |  |  |
| Ist eine Eskalationsregel anzupassen? |  |  |

---

## 7. Truth- und Evidenzcheck

| Frage | Antwort | Begründung |
|---|---|---|
| Gibt es einen maschinenlesbaren Nachweis? |  |  |
| Ist PostgreSQL als finale Wahrheitsquelle erforderlich? |  |  |
| Reicht ein bestehender Report-Scope aus? |  |  |
| Müssen neue Reports oder Validatoren ergänzt werden? |  |  |
| Kann die Aussage später reproduziert werden? |  |  |
| Besteht Risiko für `unknown`, `partial`, `watch` oder `blocked`? |  |  |

### Erwartete Evidenz

```text
Betroffene Reports:
Betroffene Tests:
Neue Reports:
Neue Validatoren:
Erwarteter finaler Status:
```

---

## 8. No-Go-Prüfung

Wenn einer dieser Punkte mit `ja` beantwortet wird, ist das Vorhaben grundsätzlich abzulehnen oder grundsätzlich umzuschneiden.

| No-Go | Ja/Nein | Begründung |
|---|---|---|
| Ersetzt die Änderung maschinenlesbare Wahrheit durch Dokumentation oder manuelle Bewertung? |  |  |
| Führt sie stille Auto-Reparaturen ein? |  |  |
| Führt sie globale Mutation ohne zwingenden Grund ein? |  |  |
| Schwächt sie Workspace-Isolation? |  |  |
| Schwächt sie Restore-Fähigkeit? |  |  |
| Verändert sie historische Snapshots still? |  |  |
| Führt sie neue Queue-/Retry-Semantik ohne Idempotenz und Aging-Erkennung ein? |  |  |
| Führt sie persistente Artefakte ohne Cleanup-/Backup-/Restore-Bewertung ein? |  |  |

### No-Go-Ergebnis

```text
No-Go festgestellt: ja / nein
Begründung:
```

---

## 9. Welche Feature-Art ist das strategisch?

Bitte zuordnen:

| Kategorie | Trifft zu? | Begründung |
|---|---|---|
| stabilitätssteigernd |  |  |
| nachweissteigernd |  |  |
| restore-/recovery-stärkend |  |  |
| drift-reduzierend oder drift-sichtbar machend |  |  |
| rein nutzerseitiger Komfortgewinn |  |  |
| neue operative Komplexität |  |  |
| neue Governance-Pflicht |  |  |
| strategisch abzulehnende Feature-Art |  |  |

---

## 10. Unverhandelbare Architekturprinzipien

Hier ist für jedes Prinzip zu dokumentieren, ob es eingehalten, erweitert oder gefährdet wird.

| Prinzip | Status | Begründung |
|---|---|---|
| PostgreSQL-Truth-Gates für finale Aussagen |  |  |
| persistente Queue |  |  |
| explizite Lifecycle- und Queue-Zustände |  |  |
| Workspace-Isolation auf allen Pfaden |  |  |
| Historical Citations bleiben erhalten |  |  |
| Drift vor Repair sichtbar machen |  |  |
| Cleanup ist dry-run-first und governance-pflichtig |  |  |
| Reindex ist auditiert und validierungspflichtig |  |  |
| Backup und Restore sind Pflichtbestandteile |  |  |
| maschinelle Nachweise schlagen Dokumentation |  |  |
| Scope-Minimierung vor globaler Wirkung |  |  |
| Reparierbarkeit wird nicht geschwächt |  |  |

---

## 11. Review-Entscheidung

```text
Entscheidung:
- freigeben
- freigeben mit Auflagen
- zurückstellen
- ablehnen

Begründung:
```

### Auflagen oder Bedingungen

```text
1.
2.
3.
```

### Pflicht-Follow-ups

```text
Tests:
Reports:
Runbooks:
Governance-Updates:
Rollback-/Restore-Anpassungen:
```

---

## 12. Abschlussbewertung in einem Satz

```text
Diese Änderung ist strategisch sinnvoll / nur eingeschränkt sinnvoll / strategisch falsch, weil ...
```
