# Feature Governance Model

Stand: 2026-05-13

## Ziel

Neue Features werden kontrolliert eingeführt, ohne bestehende Systemstabilität, Datenintegrität oder Gate-Wahrheit zu untergraben. Ein Feature gilt erst dann als freigabefähig, wenn seine Risikoklasse bestimmt ist und alle Pflichtnachweise vorliegen.

Dieses Modell ergänzt:

- `docs/architecture-change-governance.md`
- `docs/schema-evolution-safety-model.md`
- `docs/operational-truth-governance.md`
- `docs/postgres-truth-tests.md`

---

## 1. Geltungsbereich

Feature-governance-pflichtig ist jede Änderung, die neues fachliches oder operatives Verhalten einführt. Dazu gehören:

- neue API-Endpunkte oder neue Antwortsemantik
- neue UI-Flows oder neue Admin-Aktionen
- neue Import-, Retrieval-, Chat-, Cleanup-, Reindex- oder Backup-Funktionen
- neue Queue-Job-Typen oder Lifecycle-Übergänge
- neue Metriken, Reports oder Gate-relevante Statusaussagen
- Änderungen, die bestehende Nutzer- oder Systementscheidungen anders ausfallen lassen

Reine Dokumentationskorrekturen, Test-only-Änderungen und interne Refactorings ohne Verhaltensänderung sind nicht feature-governance-pflichtig. Sie bleiben test- und reviewpflichtig.

---

## 2. Pflichtbewertung für jedes Feature

Jedes neue Feature muss vor Implementierungsbeginn in sieben Bereichen bewertet werden. Jede Bewertung verwendet `keine`, `gering`, `mittel`, `hoch` oder `blockierend` plus kurze Begründung.

| Bereich | Pflichtfrage |
|---|---|
| Truth-Test-Plan | Welche PostgreSQL-Truth-, API-, Unit- oder E2E-Tests belegen das Feature und schützen bestehendes Verhalten? |
| Recovery-Bewertung | Was passiert bei Crash, Retry, Teilfehler, Advisory-Lock-Konflikt oder Wiederaufnahme nach Neustart? |
| Drift-Bewertung | Kann das Feature DB-vs-Index-, Lifecycle-, Citation-, Queue-, Report- oder Backup-Drift erzeugen? |
| Isolation-Bewertung | Bleiben Workspace-, User-, Rollen- und Admin-Grenzen erhalten? |
| Cleanup-Auswirkungen | Werden Daten eingeführt, die Cleanup-Regeln, Retention, Dry-Run oder Schutzregeln benötigen? |
| Backup/Restore-Auswirkungen | Müssen Backup-Manifest, Restore-Orchestrierung, Verify oder Restore-Truth angepasst werden? |
| Retrieval-Auswirkungen | Ändert das Feature Suchbarkeit, Ranking, Chunk-Auswahl, Kontextbau, Citations oder insufficient-context-Verhalten? |

Eine Teilbewertung ist verboten. Wenn ein Bereich nicht betroffen ist, muss `keine` begründet werden.

---

## 3. Risikoklassen

### Klasse F1: Low Risk

Ein Feature ist `low risk`, wenn es keine persistente Datenänderung, keine neue Lifecycle- oder Queue-Semantik und keinen Einfluss auf Retrieval, Restore oder Isolation hat.

Beispiele:

- read-only UI-Anzeige für bereits vorhandene API-Felder
- bessere Fehlermeldung ohne Statusänderung
- zusätzlicher Filter auf bestehendem read-only Endpoint

Pflichtnachweise:

- Truth-Test-Plan mit Begründung, warum kein neuer postgres_truth-Test nötig ist oder welcher bestehende Test schützt
- fokussierte Unit-/API-/Frontend-Tests
- Isolation-Bewertung
- Dokumentationsupdate, falls ein API- oder UI-Vertrag sichtbar geändert wird

### Klasse F2: Moderate Risk

Ein Feature ist `moderate risk`, wenn es bestehende persistente Daten liest oder erweitert, aber keine neue Architekturgrenze, keine destruktive Mutation und kein neues Gate benötigt.

Beispiele:

- neue read-only Admin-Diagnostik
- neue Metrik auf bestehenden Daten
- additive API-Felder auf stabilen Endpoints
- zusätzlicher Retrieval-Filter ohne neue Rankinglogik

Pflichtnachweise:

- vollständige 7-Bereichs-Bewertung
- Truth-Test-Plan mit mindestens einem regressionssichernden Test
- Recovery- und Drift-Bewertung mit konkreten Nicht-Auswirkungen oder Mitigationen
- Isolation-Test für workspace- oder rollenbezogene Sichtbarkeit
- Backup/Restore-Bewertung, auch wenn nur `keine Auswirkung`

### Klasse F3: High Risk

Ein Feature ist `high risk`, wenn es mutiert, asynchron läuft, Recovery benötigt, Retrieval beeinflusst, Cleanup-Relevanz erzeugt oder sensible Isolation berührt.

Beispiele:

- neuer Queue-Job-Typ
- mutierende Admin-Aktion
- neuer Lifecycle-Übergang
- Reindex-, Cleanup-, Repair- oder Replay-Funktion
- Änderung an Retrieval-Qualität, Ranking, Context Builder oder Citations

Pflichtnachweise:

- vollständige 7-Bereichs-Bewertung
- postgres_truth-Test oder begründeter neuer Truth-Block
- Recovery-Test für Teilfehler, Retry oder Crash-Wiederaufnahme
- Chaos-Test
- Drift-Nachweis vor/nach der Mutation
- Isolation-Test gegen Cross-Workspace- oder Rollenverletzung
- Rollback- oder Kompensationsplan
- Backup/Restore-Bewertung mit Restore-Smoke, wenn persistente Daten betroffen sind

### Klasse F4: Architecture Changing

Ein Feature ist `architecture changing`, wenn es Systemgrenzen, Datenmodell, Betriebsmodell, Gate-Logik, Wahrheitsquellen oder zentrale Service-Contracts ändert.

Beispiele:

- neue persistente Subsysteme oder externe Worker
- neue Datenbanktabellen mit Lifecycle-/Retrieval-/Queue-Bezug
- neuer Gate-Report oder neue Gate-Policy
- Änderung an Auth-/Workspace-Modell
- Ersatz der Queue-, Retrieval-, Backup- oder Truth-Test-Architektur
- Einführung einer neuen mutierenden Admin-Domäne

Pflichtnachweise:

- alle Nachweise aus Klasse F3
- vollständiger Architecture-Change-Prozess aus `docs/architecture-change-governance.md`
- Schema-Evolution-Bewertung, falls Datenbank oder Migration betroffen ist
- neues oder erweitertes Gate mit maschinenlesbarer Truth-Quelle
- dokumentierte Gate-Policy in `docs/operational-truth-governance.md` oder einem verlinkten Gate-Dokument
- explizite Migration-/Rollback-/Restore-Strategie

---

## 4. Klassifizierungsregeln

Die höchste zutreffende Regel gewinnt.

| Trigger | Mindestklasse |
|---|---|
| nur read-only, keine Persistenz, keine neue Semantik | F1 |
| additive Daten- oder API-Erweiterung ohne Mutation bestehender Semantik | F2 |
| neue Mutation, neuer Queue-Job, neuer Lifecycle-Übergang oder neue Admin-Write-Aktion | F3 |
| Retrieval-Ranking, Context Builder, Citation-Mapping oder insufficient-context-Policy ändert sich | F3 |
| Auth, Workspace-Isolation oder Rollenmodell wird verändert | F3 |
| Datenbankschema, Backup/Restore, Gate-Policy oder Truth-Quelle wird verändert | F4 |
| neues Betriebsmodell, neuer Worker oder neue Architekturgrenze | F4 |

Wenn die Klasse unklar ist, wird konservativ die höhere Klasse gewählt.

---

## 5. Pflichtnachweise

### 5.1 Truth-Test-Plan

Jedes Feature braucht einen Truth-Test-Plan:

```
Feature:
Risikoklasse:
Betroffene Truth-Bereiche:
Betroffene Testdateien:
Neue Tests:
Ausführungsbefehle:
Erwartete Reports:
Gate-Bedingung:
```

Für F3/F4 muss der Plan mindestens einen echten PostgreSQL-Nachweis enthalten oder begründen, warum ein vorhandener postgres_truth-Block das Feature vollständig abdeckt.

### 5.2 Recovery-Bewertung

Pflichtfragen:

- Kann ein Teilfehler einen inkonsistenten Zustand hinterlassen?
- Gibt es Retry-, Replay-, Dead-Letter- oder Kompensationspfade?
- Sind Advisory-Locks, Transaktionsgrenzen oder Idempotenz betroffen?
- Muss ein Crash-Test ergänzt werden?

F3/F4 brauchen einen ausführbaren Recovery-Test. F3 braucht zusätzlich einen Chaos-Test.

### 5.3 Drift-Bewertung

Pflichtfragen:

- Kann das Feature DB-vs-Index-Drift erzeugen?
- Können Lifecycle-Status, Searchability, Citations, Queue-Jobs oder Reports auseinanderlaufen?
- Gibt es Vorher/Nachher-Metriken oder einen Drift-Report?

F3/F4 brauchen einen Drift-Nachweis nach Ausführung des Feature-Pfads.

### 5.4 Isolation-Bewertung

Pflichtfragen:

- Welche Workspace-, User- und Rollenbindung gilt?
- Können globale Admin-Pfade workspace-scoped Daten sehen oder verändern?
- Sind Testfälle für Cross-Workspace-Verletzungen vorhanden?

Jedes Feature mit Nutzer-, Workspace- oder Admin-Bezug braucht einen Isolation-Test.

### 5.5 Cleanup-Auswirkungen

Pflichtfragen:

- Erzeugt das Feature neue persistente Artefakte?
- Müssen Retention, Schutzregeln oder Dry-Run-Ausgaben erweitert werden?
- Können Cleanup-Regeln historische Citations, aktive Daten oder Queue-Referenzen beschädigen?

F3/F4 mit neuen persistenten Artefakten brauchen eine Cleanup-Governance-Bewertung.

### 5.6 Backup/Restore-Auswirkungen

Pflichtfragen:

- Muss das Backup-Manifest erweitert werden?
- Werden neue Dateien, Tabellen, Reports oder Konfigurationen restore-relevant?
- Muss `BackupRestoreService.verify_backup()` angepasst werden?
- Braucht der Restore-Truth-Test einen neuen Assert?

F4 braucht ein neues oder erweitertes Restore-Gate, wenn restore-relevante Artefakte eingeführt werden.

### 5.7 Retrieval-Auswirkungen

Pflichtfragen:

- Ändert das Feature, welche Chunks suchbar sind?
- Ändert es Ranking, Query Parsing, Context Builder, Citation Mapping oder insufficient-context-Regeln?
- Bleiben historische Citations lesbar?
- Wird Retrieval Quality gegen Baseline verglichen?

F3/F4 mit Retrieval-Auswirkung brauchen einen Retrieval-Regressionstest und Citation-Prüfung.

---

## 6. Gate-Regeln

1. F1 darf ohne neues Gate freigegeben werden, wenn die bestehende Testabdeckung begründet ist. Quelle: `reports/current/masterplan_status.json`.
2. F2 nutzt bestehende Gates, muss aber die betroffenen Nachweise aktualisieren.
3. F3 braucht einen Chaos-Test und darf ohne bestandenen Recovery-/Drift-/Isolation-Nachweis nicht gemergt werden.
4. F4 braucht ein neues oder erweitertes Gate. Ohne maschinenlesbare Truth-Quelle bleibt der Status `not_verified`.
5. Ein Feature darf nicht als abgeschlossen dokumentiert werden, solange sein Pflichtnachweis fehlt.
6. SQLite, Mocks oder manuelle Prüfung dürfen Feature-Entwicklung unterstützen, aber kein F3/F4-Gate ersetzen.

---

## 7. Feature-Control-Prozess

### Phase 1: Intake

1. Feature in einem Satz beschreiben.
2. Nutzer- oder Systemnutzen benennen.
3. Nicht-Ziele und explizite Scope-Grenzen festhalten.
4. Vorläufige Risikoklasse bestimmen.

### Phase 2: Evidence Design

1. Sieben Pflichtbewertungen aus Abschnitt 2 ausfüllen.
2. Truth-Test-Plan erstellen.
3. Für F3/F4: Chaos-/Recovery-/Drift-Nachweise planen.
4. Für F4: neues Gate oder Gate-Erweiterung definieren.

### Phase 3: Implementierung

1. Tests und Gate-Artefakte parallel zum Feature implementieren.
2. Neue persistente Artefakte in Cleanup und Backup/Restore berücksichtigen.
3. Isolation und Retrieval-Auswirkungen nicht nachträglich behandeln.

### Phase 4: Verifikation

1. Relevante Fast-Feedback-Tests ausführen.
2. PostgreSQL-Truth-Nachweise ausführen, wenn Klasse F3/F4 oder Gate-relevant.
3. Chaos-Test für F3/F4 ausführen.
4. Reports prüfen: `failed = 0`, `errors = 0`, `skipped = 0` für Pflichtgates.

### Phase 5: Freigabe und Dokumentation

1. Risikoklasse und Nachweise dokumentieren.
2. Gate-Status nur aus Reports oder Validatoren ableiten.
3. `docs/status.md`, `docs/postgres-truth-tests.md`, `masterplan.md` und betroffene Fachdocs aktualisieren.
4. Offene Nachweise als `not_verified`, `partial`, `watch` oder `blocked` markieren, nicht als `pass`.

---

## 8. Kurzcheckliste

```
[ ] Feature-Klasse F1/F2/F3/F4 bestimmt
[ ] Alle 7 Pflichtbewertungen ausgefüllt
[ ] Truth-Test-Plan dokumentiert
[ ] Recovery-Bewertung abgeschlossen
[ ] Drift-Bewertung abgeschlossen
[ ] Isolation-Bewertung abgeschlossen
[ ] Cleanup-Auswirkungen bewertet
[ ] Backup/Restore-Auswirkungen bewertet
[ ] Retrieval-Auswirkungen bewertet
[ ] Für F3/F4: Chaos-Test geplant und ausgeführt
[ ] Für F4: neues oder erweitertes Gate definiert
[ ] Reports/Validatoren belegen den behaupteten Status
[ ] Dokumentation aktualisiert
```
