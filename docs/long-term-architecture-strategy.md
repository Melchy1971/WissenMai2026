# Langfristige Architekturstrategie

Stand: 2026-05-13

## Zeithorizont und Grundannahme

Dieses Dokument plant für mehrere Jahre aktiven Betriebs. Die Grundannahme: Ein Wissens- und RAG-System alteriert. Daten akkumulieren, Indexe divergieren, Queue-Muster verschieben sich, Migrationen stapeln sich, Retrieval-Qualität erodiert ohne Gegensteuern. Das ist kein Fehlerfall — das ist die Normalerwartung an ein lebendiges System.

Strategie bedeutet daher nicht "was bauen wir als nächstes", sondern: welche Eigenschaften muss das System in Jahr 3 noch haben, und welche Entscheidungen von heute gefährden das?

Verwandte Dokumente:

- `docs/strategic-target-state.md` — Zielbild, Prinzipien, No-Go-Katalog (Grundlage dieses Dokuments)
- `docs/long-term-governance-review.md` — aktueller Governance-Stand und Lücken
- `docs/system-invariant-registry.md` — nicht verhandelbare Systemgarantien
- `docs/feature-governance-model.md` — Feature-Klassifizierung und Pflichtnachweise

---

## 1. Strategische Ziele mit Langzeitbindung

### Ziel 1: Deterministische Wahrheit

Das System produziert zu jedem Zeitpunkt einen maschinenlesbaren, scope-korrekten und reproduzierbaren Nachweis über seinen eigenen Zustand. Wahrheit ist kein Redaktionsprozess.

**Langzeit-Leitplanke**: Kein neues Subsystem darf seinen eigenen konkurrierenden Wahrheitsbegriff einführen. Jede neue Truth-Quelle muss explizit in `docs/operational-truth-governance.md` registriert werden.

**Degradierungssignal**: Wenn Wahrheit nur noch aus mehreren inkonsistenten Reports rekonstruiert werden kann, ist das Subsystem strategisch krank.

---

### Ziel 2: Kontrollierte Evolution

Das System entwickelt sich durch bewertete Änderungen, nicht durch akkumulierte Spontanentscheidungen. Jede Architekturänderung ist bewertbar, rückführbar und gate-geprüft.

**Langzeit-Leitplanke**: Der Change-Control-Prozess (`docs/architecture-change-governance.md`) ist für jede Architekturänderung verpflichtend — auch wenn das Team wächst, auch wenn Zeitdruck entsteht.

**Degradierungssignal**: Wenn mehr als 30 % der Commits in einem Monat keine Impact-Bewertung für betroffene Stabilitätsbereiche enthalten, verliert das System seine kontrollierte Evolutionsfähigkeit.

---

### Ziel 3: Auditierbare Reparaturen

Jede Repair-Aktion ist rückverfolgbar zu einer Ursache, einem Auslöser, einem Ergebnis und einem Verifikationsartefakt. Niemand repariert still.

**Langzeit-Leitplanke**: Das `actor`-Feld in Audit-Events (L-03 aus Governance Review) muss vor dem ersten produktiven Betrieb mit mehreren Benutzern vollständig implementiert sein.

**Degradierungssignal**: Wenn Incidents nicht mehr einem Auslöser zugeordnet werden können, ist die Audit-Kette unterbrochen.

---

### Ziel 4: Drift-resistente Datenhaltung

Stale Index, Orphan Chunks und Citation-Degradation sind nicht Ausnahmen, die bei Gelegenheit bereinigt werden — sie sind messbare Betriebsgrößen mit definierten Schwellen und reaktiven Pfaden.

**Langzeit-Leitplanke**: `RETRIEVAL_COVERAGE_MIN = 0.85` ist eine Produktionsschwelle, nicht ein Testziel. Unterschreitung löst eine sofortige Reindex-Governance aus, keine Akzeptanz.

**Degradierungssignal**: `m5_drift_score > 0` persistiert über 72 Stunden ohne Repair-Aktion. Orphan-Rate wächst monoton über 30 Tage.

---

### Ziel 5: Reproduzierbare Retrieval-Qualität

RAG-Verhalten ist versioniert, benchmarked und regressionsgeschützt. Ein Benutzer, der heute eine Frage stellt, erhält dasselbe Qualitätsniveau wie in 18 Monaten — oder eine explizit kommunizierte Vertragsversionsänderung.

**Langzeit-Leitplanke**: Der Golden-Query-Korpus (`m5-retrieval-golden-v1`) wird bei jeder Retrieval-Vertragsänderung versioniert. Alte Queries werden nie gelöscht.

**Degradierungssignal**: `Citation Completeness` unter Schwelle ohne aktive neue Vertragsversion. `Retrieval Coverage` unter 0.85 ohne laufenden Reindex.

---

### Ziel 6: Sichere Recovery

Ein Produktionssystem muss sich innerhalb definierter Zeit aus einem Backup vollständig wiederherstellen lassen. Restore ist keine Notfallprozedur — er ist ein routinemäßig getesteter Betriebspfad.

**Langzeit-Leitplanke**: `BackupRestoreService.verify_backup()` wird mindestens monatlich ausgeführt. Das Ergebnis ist maschinenlesbar und referenziert in einem aktuellen Report. Backup-Freshness > 7 Tage ist ein produktionsblocker.

**Degradierungssignal**: Letzter Restore-Test älter als 90 Tage. `verify_backup()` schlägt fehl. Restore-Zeit > 120 Minuten (SLA-6).

---

### Ziel 7: Governance-first Entwicklung

Governance ist kein Bremse und kein Overhead. Governance ist die Bedingung, unter der das System langfristig kontrollierbar bleibt. Jede Abkürzung an der Governance reduziert die Kontrollierbarkeit — auch wenn das einzelne Feature schneller fertig ist.

**Langzeit-Leitplanke**: Kein Feature gelangt in Produktion ohne abgeschlossene F-Klassifizierung und Pflichtbewertungen. Kein Merge ohne bestandenen Truth-Gate.

**Degradierungssignal**: Häufung von "kleine Änderung ohne Risikoanalyse"-Commits. Gate-Ausnahmen werden zur Routine.

---

## 2. Tolerierbare technische Schulden

Technische Schulden sind tolerierbar, wenn:
- sie keine Gate-Wirkung haben
- sie nicht CRITICAL-Invarianten gefährden
- ein dokumentierter Schließungspfad existiert
- der Zeitraum bis Schließung explizit begrenzt ist

### Tolerierbare Schulden (Beispiele aus Technical Debt Register)

| ID | Schuld | Bedingung für Toleranz |
|---|---|---|
| TD-P5-003 | OCR fehlt für gescannte PDFs | klar kommuniziert; kein Datenverlust; `OCR_REQUIRED`-Fehler ist sichtbar |
| TD-P5-009 | LibreOffice-Abhängigkeit für DOC-Import | lokaler Workaround; kein Systemstabilitätsrisiko |
| TD-P5-011 | `updated_at` nicht per Trigger gepflegt | MEDIUM-Schwere; kein Gate-Blocker; Follow-up möglich |
| TD-P5-012 | Parser-Confidence-Metriken fehlen | Qualitätsschuld ohne Sicherheitsimplikation |
| L-06 | Kein zentraler Audit-Store | operativer Betrieb funktioniert; Compliance-Einschränkung bekannt |

**Toleranz-Grenze**: Eine Schuld wird intolerant, wenn sie in Kombination mit anderen Schulden oder wachsendem Datenvolumen einen Gate-Blocker erzeugt oder eine CRITICAL-Invariante gefährdet.

---

## 3. Nicht tolerierbare Architekturverletzungen (No-Go)

Die folgenden Verletzungen sind ohne Ausnahme verboten — unabhängig von Zeitdruck, Feature-Priorität oder Team-Größe. Sie sind aus `docs/strategic-target-state.md` Abschnitt 5 destilliert und mit Langzeit-Konsequenz erweitert.

| Nr. | Verletzung | Warum No-Go |
|---|---|---|
| NG-01 | Stille Auto-Repair auf Primärdaten (Lifecycle, Citations, Queue) | erzeugt unauditierbare Datenmutation; Langzeitfolge: unrekonstruierbarer Zustand |
| NG-02 | Workspace-Isolation aufheben für globale Convenience | Sicherheitsgrenze; Langzeitfolge: unkontrollierbarer Daten-Leak |
| NG-03 | Retrieval ohne Lifecycle-Filterung | CRITICAL-Invariante (INV-021, INV-022); gelöschte/archivierte Inhalte im RAG |
| NG-04 | Irreversible Migration ohne Restore-Test | Datenverlustrisiko ohne Rückfallpfad; Klasse-D-Pflicht |
| NG-05 | Gateway-Aussagen aus SQLite oder Mocks | false-positive Gate-Vertrauen; Langzeitfolge: Produktionsfehler nach scheinbar grünem Gate |
| NG-06 | Queue-Job ohne Dead-Letter-Pfad und Aging-Erkennung | stille Starvation; Langzeitfolge: Jobs verschwinden, keine Eskalation |
| NG-07 | Neues persistentes Subsystem ohne Backup/Restore-Bewertung | nicht restore-fähig; Langzeitfolge: DR-Ausfall |
| NG-08 | Citation-Mutation nach Erstellung | historische Unreproduzierbarkeit; INV-025 |
| NG-09 | Merge einer governance-pflichtigen Änderung ohne Impact Assessment | kontrollierter Evolutionsverlust; Langzeitfolge: unentdeckte Stabilitätserosion |
| NG-10 | Feature-Dokumentation als Gate-Ersatz | Wahrheit ist nie Dokumentation; systemisches Vertrauensproblem |

---

## 4. Pflichtrefactoring-Trigger

Refactoring ist verpflichtend — unabhängig von Feature-Priorität — wenn einer der folgenden Trigger eintritt:

### RF-01: Invarianten-Verletzung ohne kurzfristigen Fix

Wenn eine CRITICAL-Invariante (INV-021 bis INV-036) länger als 48 Stunden verletzt ist und kein unmittelbarer Fix-Pfad existiert, muss ein Refactoring-Sprint geplant werden. Neue Features pausieren.

### RF-02: STALE_RATE > STALE_RATE_MAX über 14 Tage

Persistenter Index-Drift über zwei Wochen bedeutet, dass die Lifecycle-Filterung strukturell fehlerhaft ist, nicht nur operativ überlastet. Refactoring des Reindex-Pfads ist Pflicht.

### RF-03: Dead-Letter-Rate steigt über 3 Monate monoton

Monoton wachsender Dead-Letter-Bestand bedeutet systematische Fehlerklassen, die durch Retry nicht auflösbar sind. Job-Typ, Retry-Logik oder Verarbeitungsarchitektur ist zu refaktorieren.

### RF-04: Restore-Zeit überschreitet SLA-6 (> 120 min) dauerhaft

Wenn der Restore-Prozess chronisch SLA verletzt, ist die Backup/Restore-Architektur zu überarbeiten. Neue Migrations-Klassen C/D sind bis zum Fix blockiert.

### RF-05: Alembic-Migrations-Kette hat > 30 Revisionen ohne Merge-Migration

Lange, lineare Migrationsketten erzeugen fragile Upgrade-Pfade. Nach 30 Revisionen ist eine konsolidierte Baseline-Migration Pflicht.

### RF-06: Test-Laufzeit > 10 Minuten für postgres_truth-Suite

Wenn die Truth-Suite zu langsam wird, wird sie übersprungen. Refactoring der Test-Infrastruktur (Fixture-Isolation, Parallelisierung) ist Pflicht.

### RF-07: `actor`-Feld fehlt vor erstem Mehrbenutzerbetrieb

Lücke L-03 aus Governance Review: vor Aktivierung mit mehreren Benutzern in Produktion ist die Audit-Trail-Implementierung zu vervollständigen. Kein Mehrbenutzerbetrieb ohne vollständige Accountability-Kette.

---

## 5. Feature-Stop-Bedingungen

Feature-Entwicklung muss pausieren, wenn:

### FS-01: Zwei oder mehr CRITICAL-Invarianten gleichzeitig verletzt

Wenn INV-021 (Retrieval-Filterung), INV-023 (Workspace-Isolation) oder INV-025 (Citation-Stabilität) gleichzeitig verletzt sind, ist Systemstabilität nicht mehr garantiert. Feature-Stop sofort; Incident-Modus.

### FS-02: `TEST_DATABASE_URL` in CI nicht verfügbar

Solange Truth-Tests nicht gegen echte PostgreSQL laufen, gibt es keine vertrauenswürdige Gate-Aussage. Neue Features, die Schemamigrationen, Retrieval, Queue oder Lifecycle berühren, dürfen nicht gemergt werden.

### FS-03: `m5_backup_freshness_seconds` > 7 Tage (kritische Schwelle)

Kein Merge von Klasse-C/D-Migrationen, Cleanup-Mutations oder Retrieval-Architekturänderungen ohne aktuelles, verifiziertes Backup.

### FS-04: Drei oder mehr offene KRIT-Mitigationen aus Risk-Matrix

Wenn drei oder mehr ungeklärte KRIT-Einträge im aktuellen Risk-Matrix-Stand existieren, ist die technische Schuld zu groß für sicheres Feature-Wachstum. Governance-Sprint vor nächstem Feature-Sprint.

### FS-05: Governance-Prozess nicht eingehalten in letzten 30 Tagen

Wenn in den letzten 30 Tagen eine governance-pflichtige Änderung ohne vollständige Artefakte gemergt wurde, ist der Change-Control-Prozess zu re-etablieren und zu auditieren, bevor neue Features gestartet werden.

---

## 6. Evolutionsregeln

### E-01: Jede Schicht hat einen kanonischen Eigentümer

Service-Schicht, Repository-Schicht, Queue, Reindex, Cleanup, Retrieval und Citation sind keine gemeinsamen Bereiche. Neue Features, die Schichten überqueren, brauchen explizite Architektur-Entscheidung.

### E-02: Neue Persistenz-Grenzen erfordern vollständige Lifecycle-Planung

Ein neues persistentes Artefakt (Tabelle, Datei, Report, Cache) muss beim Anlegen dokumentieren: wer erstellt es, wer liest es, wann wird es bereinigt, wie wird es in Backup und Restore integriert.

### E-03: Metriken akkumulieren nicht ohne Archivierungs-Policy

Jede neue Metrik oder jeder neue Report-Typ muss beim Anlegen eine Retention-Regel definieren. Unbegrenzt wachsende Artefakt-Sammlungen sind keine Langzeitstrategie.

### E-04: Neue Subsysteme erben alle Governance-Dokumente

Ein neues Subsystem (z.B. OCR-Service, Semantic-Ranking-Service) untersteht denselben Truth-, Audit-, Lifecycle- und Recovery-Regeln wie das Kernsystem. Kein Subsystem bekommt einen Governance-Sonderstatus.

### E-05: Governance-Dokumente sind lebende Artefakte

Governance-Dokumente werden nach jedem Milestone und nach jedem Incident-Review aktualisiert. Ein Governance-Dokument, das länger als 6 Monate ohne Update ist, wird auf Aktualität geprüft.

### E-06: Refactoring-Schulden haben Verfallsdaten

Jede tolerierte technische Schuld (Abschnitt 2) bekommt ein spätestes Schließungsdatum. Überschrittene Schließungsdaten werden beim nächsten Milestone-Review eskaliert.

---

## 7. Langfristige Architekturentscheidungen — Leitplanken

| Entscheidung | Leitplanke | Revisionsbedingung |
|---|---|---|
| PostgreSQL als finale Truth | wird nicht durch andere DBs ersetzt | nur wenn PostgreSQL fundamentale Kapazitäts- oder Skalierungsgrenze erreicht AND Migrationspfad ohne Governance-Verlust existiert |
| Persistente Queue (DB-backed) | wird nicht durch flüchtigen In-Memory-Broker ersetzt | nur wenn Queue-Volumen PostgreSQL strukturell überfordert AND alle Queue-Invarianten auf neuem System nachweisbar |
| Explizite Lifecycle-Zustände | keine impliziten Soft-Delete-Mechanismen | nie: implizite Mechanismen sind No-Go-02 |
| Workspace-Isolation durch Session-Binding | kein globaler Lesepfad ohne explizite Workspace-Grenze | nie: Workspace-Isolation ist NG-02 |
| Governance-First-Prozess | kein Feature-Track außerhalb der Governance | nie: Ausnahmen werden zur Regel |
| Maschinenlesbare Gate-Artefakte | kein Markdown-Report als alleinige Gate-Grundlage | nie: maschinenlesbare Gates sind nicht verhandelbar |

---

## 8. Strategische Abschlussformel

Das System wächst nicht dadurch, dass es immer mehr kann.
Es wächst dadurch, dass es mehr Verantwortung **sicher** tragen kann.

Eine Architekturentscheidung ist langfristig richtig, wenn sie in Jahr 3 noch kontrollierbar, auditierbar, reparierbar und restore-fähig ist — und wenn sie das für alle anderen Entscheidungen ebenfalls erleichtert, nicht schwieriger macht.

Alles andere ist technische Schuld mit Verfallsdatum.
