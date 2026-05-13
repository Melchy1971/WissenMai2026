# Strategisches Zielbild

Stand: 2026-05-13

## Zielzustand

Der strategische Zielzustand dieses Systems ist nicht maximale Feature-Dichte, sondern ein langlebiges Wissens- und Betriebsystem, das unter Veraenderung, Last, Wiederherstellung und Alterung kontrollierbar bleibt.

Das System soll langfristig:

- konsistent bleiben
- kontrollierbar bleiben
- auditierbar bleiben
- reparierbar bleiben
- Drift frueh erkennen
- deterministisch reagieren
- aus Backup und Restore belastbar wiederherstellbar sein

Der Zielzustand ist erreicht, wenn neue Funktionen nicht vor allem mehr Verhalten erzeugen, sondern innerhalb eines klaren Rahmens beweisbar, wiederholbar und rueckfuehrbar bleiben.

## Strategisches Zielbild

### 1. Das System ist ein kontrolliertes Wissenssystem, kein Feature-Sammelbecken

Der Wert des Systems entsteht aus verlaesslicher Dokument-, Retrieval-, Citation-, Queue- und Restore-Konsistenz. Ein Feature ist nur dann strategisch sinnvoll, wenn es diese Eigenschaften erhaelt oder verbessert.

### 2. Das System ist auf Alterung vorbereitet

Langfristiger Betrieb wird als Normalfall behandelt. Das System muss deshalb Orphans, stale Indexzustände, Queue-Backlog-Drift, Retry-Akkumulation, Citation-Degradation und Retrieval-Regression nicht nur technisch ueberstehen, sondern sichtbar machen.

### 3. Das System bleibt reparierbar

Jeder kontrollierte Repair-Pfad muss enger begrenzt, auditierbar und sicherer sein als der Schaden, den er behebt. Repair darf nie still, global oder erratend arbeiten.

### 4. Das System bleibt wahrheitsgebunden

Statusaussagen duerfen nicht aus Hoffnung, Dokumentation oder Einzelbeobachtungen entstehen. Wahrheit entsteht nur aus aktuellen, maschinenlesbaren und scope-korrekten Nachweisen.

### 5. Das System bleibt betrieblich fuehrbar

Betrieb ist kein Nebenthema der Entwicklung. Queue, Drift, Reindex, Cleanup, Restore, Truth und Retrieval muessen als laufende operative Disziplinen gefuehrt werden.

## 1. Technische Prinzipien

1. Determinismus vor Bequemlichkeit.
   Gleichartige Inputs, Datenstaende und Konfigurationen muessen zu nachvollziehbar gleichen Ergebnissen fuehren.

2. Kanonische Datenquelle vor abgeleiteten Sichtmodellen.
   Suchindex, Reports, Health Scores und andere Ableitungen duerfen Primaerdaten nie ersetzen.

3. Persistente Fachzustaende vor fluechtigen Laufzeitannahmen.
   Queue, Lifecycle, Restore, Retry und Recovery duerfen nicht von In-Memory-Zustand oder Prozesszufall abhaengen.

4. Explizite Zustandsuebergaenge vor impliziter Magie.
   Lifecycle-, Queue-, Citation- und Governance-Status duerfen nur ueber explizite Regeln mutieren.

5. Kleine, begrenzte Repair-Scope vor globalen Reparaturen.
   Document-scoped oder workspace-scoped Repair ist strategisch vorzuziehen; globale Repair- oder Reindex-Schritte sind Ausnahmefaelle.

6. Idempotenz vor wiederholbarer Schaedenserzeugung.
   Retry, Replay, Restore, Reindex und Cleanup muessen mehrfach ausfuehrbar sein, ohne neue Inkonsistenzen zu erzeugen.

7. Historische Nachvollziehbarkeit vor nachtraeglicher Schoenfaerbung.
   Historical Citations, Audit-Artefakte und Truth-Reports duerfen nicht still ueberschrieben werden, nur damit der aktuelle Zustand sauber wirkt.

8. Rebuildbarkeit vor Sonderwissen.
   Suchindexe, Reports und abgeleitete Metriken muessen aus kanonischen Quellen erneut aufbaubar sein.

9. Workspace-Isolation vor Bequemlichkeitsabkuerzungen.
   Kein technischer Pfad darf Isolation aushebeln, nur weil globales Operieren einfacher erscheint.

10. Restore-Faehigkeit ist Teil des Designs, nicht Nachdokumentation.
    Neue persistente Artefakte sind nur zulaessig, wenn ihre Backup-, Verify- und Restore-Auswirkungen explizit bewertet sind.

## 2. Governance-Prinzipien

1. Kein Feature ohne Risikoklassifikation.

2. Kein Architektur-Eingriff ohne Impact Assessment, Risk Matrix, Truth-Test-Plan und Rollback-Plan.

3. Die hoechste betroffene Risikoklasse gewinnt.
   Wenn eine Aenderung gleichzeitig klein wirkt und Retrieval, Queue oder Restore beruehrt, gilt die hoehere Klasse.

4. Scope muss kleiner werden, nicht groesser.
   Jede neue Mutation, Admin-Aktion oder Architekturgrenze muss begruenden, warum kein kleinerer Scope ausreicht.

5. Governance gilt auch fuer Betriebsfeatures.
   Reindex, Cleanup, Repair, Backup, Restore, Queue-Recovery und Drift-Kontrolle sind keine Sonderzonen ausserhalb der Governance.

6. Dokumentation beschreibt Regeln, sie ersetzt keine Nachweise.

7. Ein gruener Teilscope darf nie als gruener Gesamtscope ausgegeben werden.

8. Neue Features duerfen bestehende Governancerahmen nicht unterlaufen.
   Ein Feature, das Audit, Truth, Restore oder Isolation umgeht, ist strategisch falsch, auch wenn es fachlich attraktiv wirkt.

## 3. Betriebsprinzipien

1. Read-only Diagnose vor mutierendem Eingriff.
   Zuerst beobachten, dann klassifizieren, dann begrenzt handeln.

2. Detect first, repair second.
   Das System soll Drift, Aging und Inkonsistenzen zuerst sichtbar machen. Automatische Reparatur ist nicht der Standard.

3. Dry run first.
   Cleanup, Repair und andere riskante Vorgänge muessen zuerst eine nicht-destruktive Auswertung erzeugen.

4. Backup vor mutierender Betriebsaktion.
   Kein riskanter Reindex, kein destructive Cleanup, kein grosser Repair und kein Restore-naher Eingriff ohne aktuellen Verify- oder Restore-Nachweis.

5. Betriebsfreigabe nur aus aktuellen Reports.

6. Operative Entscheidungen brauchen Scope, Zeitpunkt und Nachweisquelle.

7. Langzeitbetrieb ist ein Pflichtszenario.
   Wochen-, Drift- und Entropy-Zyklen sind fester Betriebsbestandteil, kein optionaler Testmodus.

8. Eskalation ist Teil des Designs.
   Ein System ohne klare L0-L4-Eskalation ist strategisch nicht reif.

## 4. Truth-Prinzipien

1. Wahrheit ist maschinenlesbar.

2. PostgreSQL ist finale Wahrheit fuer relevante Gates.
   SQLite, Mocks und In-Memory-Laeufe sind Entwicklungswerkzeuge, aber keine Freigabequelle fuer drift-, restore-, isolation- oder queue-kritische Aussagen.

3. Wahrheit ist scope-gebunden.
   Ein Report darf nur die Aussage staerken, die sein Scope wirklich abdeckt.

4. Wahrheit ist zeitgebunden.
   Historische gruene Artefakte ersetzen keine aktuellen Nachweise.

5. Wahrheit ist reproduzierbar.
   Report, Umgebung, Command, Exit-Code, Datenbanktyp und Commit muessen nachvollziehbar sein.

6. Wahrheit ist konfliktfest.
   Widerspricht Dokumentation einem maschinenlesbaren Report, gewinnt der Report.

7. Wahrheit ist konservativ.
   Fehlende Evidenz erzeugt `unknown`, `partial`, `watch` oder `blocked`, niemals kuenstliches `pass`.

## 5. No-Go-Prinzipien

1. Keine Features, die nur mehr Verhalten erzeugen, aber keine kontrollierbare Evidenz.

2. Keine stillen Auto-Repairs auf Primaerdaten, Lifecycle, Citations oder Queue-Zustaenden.

3. Keine globalen Admin-Mutationen ohne Governance, Audit und Scope-Begruendung.

4. Keine Architekturabkuerzung, die Workspace-Isolation, Restore-Faehigkeit oder Truth-Pfade schwaecht.

5. Keine Freigabeaussage aus Dokumentation allein.

6. Keine produktionsnahe Behauptung auf Basis von SQLite, Mocks oder Teilscopes.

7. Keine irreversiblen Datenpfade ohne explizite Rollback- und Restore-Bewertung.

8. Keine Features, die historische Nachvollziehbarkeit durch stilles Ueberschreiben zerstören.

9. Keine Queue- oder Retry-Semantik ohne Idempotenz, Dead-Letter-Pfad und Aging-Erkennung.

10. Keine neuen persistierenden Artefakte ohne Cleanup-, Backup- und Restore-Bewertung.

## Welche Arten von Features kuenftig abgelehnt werden?

Die folgenden Feature-Arten sind strategisch abzulehnen, auch wenn sie kurzfristig attraktiv wirken:

1. Features, die global mutieren, obwohl ein dokument- oder workspace-scoped Pfad moeglich waere.

2. Features, die neue Betriebszustände erzeugen, aber keinen Truth-, Drift- oder Recovery-Nachweis mitbringen.

3. Features, die Ranking, Retrieval, Citation Mapping oder Context Builder aendern, ohne Regression- und Longevity-Nachweis.

4. Features, die neue Queue- oder Retry-Semantik einfuehren, ohne Idempotenz, Replay-Sicherheit und Aging-Erkennung.

5. Features, die operative Komplexitaet erhoehen, aber keine direkte Stabilitaets-, Nachweis- oder Recovery-Verbesserung erzeugen.

6. Features, die Daten nur duplizieren, spiegeln oder zwischenspeichern, ohne klaren kanonischen Eigentuermer.

7. Features, die "smarte" automatische Korrekturen versprechen, aber weder deterministisch noch auditierbar sind.

8. Features, die neue Admin-Schreibaktionen einführen, ohne Governance-Report, Dry Run und Rollback-Pfad.

9. Features, die Restore-relevante Artefakte einfuehren, ohne Verify- und Restore-Erweiterung.

10. Features, die starke Produktivitaets- oder Komfortgewinne versprechen, aber dafuer Wahrheit, Determinismus oder Reparierbarkeit schwaechen.

## Welche Architekturprinzipien sind unverhandelbar?

Diese Prinzipien gelten als nicht verhandelbar:

1. PostgreSQL-basierte Truth-Gates fuer alle relevanten finalen Betriebs- und Freigabeaussagen.

2. Persistente Queue statt fluechtiger Zuverlaessigkeitsannahmen.

3. Explizite Lifecycle- und Queue-Zustaende statt impliziter Seiteneffekte.

4. Workspace-Isolation auf allen Lese-, Schreib-, Diagnose- und Repair-Pfaden.

5. Historical Citations bleiben erhalten und werden nicht still ueberschrieben.

6. Drift muss messbar sein und vor mutierenden Repair-Aktionen sichtbar werden.

7. Cleanup ist governance-pflichtig, dry-run-first und ohne Schutzverletzung.

8. Reindex ist governance-pflichtig, auditiert und immer mit nachgelagerter Validierung.

9. Backup und Restore sind Pflichtbestandteile jeder persistenten Architekturentscheidung.

10. Maschinelle Nachweise schlagen dokumentarische Behauptungen.

11. Scope-Minimierung vor globaler Wirkung.

12. Kein strategischer Ausbau, der die Reparierbarkeit des Systems reduziert.

## Langfristige Architekturregeln

### A. Daten und Ableitungen

- Primaerdaten bleiben von Ableitungen getrennt.
- Suchindex, Reports, Health Scores und Repair-Entscheidungen bleiben aus Primaerdaten rekonstruierbar.
- Kein neues Subsystem darf seine eigene konkurrierende Wahrheit etablieren.

### B. Mutation und Recovery

- Jede Mutation braucht einen klaren Eigentuemer-Service.
- Jeder Recovery-Pfad braucht Idempotenz, Audit und Nachpruefung.
- Kein Retry darf neue Datenverdopplung oder stille Inkonsistenz erzeugen.

### C. Drift und Aging

- Drift wird als dauerhafte Systemeigenschaft angenommen, nicht als Ausnahme.
- Langzeitmetriken sind Pflicht fuer Queue, Retrieval, Citations, Index und Cleanup.
- Jede groeßere Architekturentscheidung muss beantworten, wie sie Drift sichtbar macht statt ihn zu verdecken.

### D. Governance und Freigabe

- Neue Features dürfen nur innerhalb bestehender Governancerahmen oder mit deren expliziter Erweiterung entstehen.
- Ein neues Gate braucht eine neue Truth-Quelle und klare Pass-/Fail-Regeln.
- Kein Slice darf gruen dokumentiert werden, wenn nur Vorbereitung oder Teilabdeckung vorliegt.

### E. Betrieb und Wiederherstellung

- Operativer Normalbetrieb und Wiederherstellung muessen beide designt sein.
- Restore-Faehigkeit ist keine Incident-Sonderfunktion, sondern Daueranforderung.
- Jede neue persistente oder mutierende Funktion muss in Backup, Restore, Drift und Cleanup eingeordnet werden.

## Strategische Abschlussformel

Dieses System soll nicht dadurch wachsen, dass es immer mehr kann, sondern dadurch, dass es mehr Verantwortung sicher tragen kann.

Strategisch richtig ist deshalb nur, was mindestens einen dieser Effekte hat:

- es reduziert Inkonsistenzrisiko
- es verbessert Nachweisbarkeit
- es verbessert Wiederherstellbarkeit
- es verbessert Drift-Erkennung
- es verbessert Reparierbarkeit
- es erhoeht Determinismus unter Last und Langzeitbetrieb

Alles andere ist nachrangig.
