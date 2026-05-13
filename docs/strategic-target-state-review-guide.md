# Strategisches Zielbild fuer PR- und Architektur-Reviews

Stand: 2026-05-13

## Zweck

Diese Leitversion uebersetzt das strategische Zielbild in eine kurze Review-Hilfe fuer Pull Requests, Architekturentscheidungen und neue Features.

Sie beantwortet nicht, ob etwas interessant ist, sondern ob es strategisch zum System passt.

Referenzdokument:

- `docs/strategic-target-state.md`

## Kernfrage

Staerkt die Aenderung die langfristige Konsistenz, Kontrollierbarkeit, Auditierbarkeit, Reparierbarkeit, Drift-Erkennung, Deterministik oder Restore-Faehigkeit des Systems?

Wenn die Antwort nicht klar `ja` ist, ist die Aenderung mindestens begruendungspflichtig.

## PR-Kurzpruefung

Jeder PR und jede Architekturentscheidung sollte vor Freigabe diese 10 Fragen beantworten:

1. Macht die Aenderung das System kontrollierbarer statt nur groesser?
2. Bleibt der fachliche und technische Zustand deterministisch und reproduzierbar?
3. Entsteht neue Drift-, Retry-, Cleanup-, Reindex- oder Restore-Komplexitaet?
4. Gibt es fuer die Aenderung einen klaren Truth-, Drift- oder Recovery-Nachweis?
5. Bleibt Workspace-Isolation auf allen betroffenen Pfaden erhalten?
6. Ist der Scope minimal genug oder wird unnötig global mutiert?
7. Bleiben Historical Citations, Audit-Artefakte und andere Historienpfade unangetastet?
8. Ist die Aenderung backup-, restore- und cleanup-bewertet, falls sie persistente Artefakte einführt?
9. Wird kein neuer Betriebszustand eingefuehrt, der nicht beobachtbar oder reparierbar ist?
10. Ist die Aenderung strategisch noch richtig, wenn sie 1000-mal, nach Monaten Betrieb oder nach einem Restore ausgefuehrt werden muss?

## Review-Entscheidungen

### Freigeben

Die Aenderung ist strategisch passend, wenn:

- sie Stabilitaet oder Nachweisbarkeit verbessert
- sie keinen unverhandelbaren Architekturgrundsatz verletzt
- sie keine unkontrollierte neue Betriebs- oder Datenkomplexitaet erzeugt
- die benoetigten Nachweise und Grenzen explizit vorhanden sind

### Freigeben mit Auflagen

Die Aenderung ist nur mit Auflagen passend, wenn:

- der Nutzen plausibel ist, aber Nachweise noch nachgezogen werden muessen
- der Scope noch reduziert werden sollte
- Drift-, Recovery- oder Restore-Auswirkungen noch nicht sauber dokumentiert sind
- Governance oder Runbook-Anteile im selben PR oder direkt danach geschlossen werden muessen

### Ablehnen

Die Aenderung ist strategisch falsch, wenn:

- sie nur mehr Verhalten erzeugt, aber keine beherrschbare Evidenz
- sie globale Mutation statt minimalem Scope waehlt
- sie Wahrheit, Auditierbarkeit oder Restore-Faehigkeit schwaecht
- sie Workspace-Isolation oder Historical Citations gefaehrdet
- sie neue Queue-, Retry-, Cleanup- oder Repair-Semantik ohne Governance einführt

## Unverhandelbare Review-Regeln

Ein PR oder Architekturvorschlag ist ohne weitere Diskussion abzulehnen, wenn mindestens einer dieser Punkte zutrifft:

1. Er ersetzt maschinenlesbare Wahrheit durch Dokumentation, Mocks oder manuelle Bewertung.
2. Er fuehrt globale oder stille Reparaturen ohne Audit und Scope-Begrenzung ein.
3. Er unterlaeuft Workspace-Isolation.
4. Er verändert persistente oder operative Pfade ohne Backup-/Restore-Bewertung.
5. Er verändert Retrieval-, Citation- oder Context-Logik ohne Regression- oder Longevity-Nachweis.
6. Er fuehrt neue Queue- oder Retry-Logik ohne Idempotenz, Dead-Letter-Pfad und Aging-Erkennung ein.
7. Er ueberschreibt historische Snapshots oder Audit-Artefakte still.
8. Er vergroessert den Scope eines Eingriffs, obwohl ein kleinerer Scope ausreicht.

## Architektur-Review-Fragen

Bei Architekturentscheidungen sind zusaetzlich diese Fragen verbindlich:

1. Wo liegt die kanonische Wahrheit nach der Aenderung?
2. Welche Ableitungen entstehen neu und wie werden sie verifiziert oder neu aufgebaut?
3. Wie wird Drift nach der Aenderung sichtbar?
4. Wie wird ein Teilfehler, Retry oder Crash nach der Aenderung sicher aufgefangen?
5. Welche Runbooks, Gates oder Reports muessen mitgezogen werden?
6. Wie wird Restore-Faehigkeit durch die Aenderung erhalten oder verbessert?
7. Welche Feature-Klassen werden dadurch spaeter einfacher und welche gefaehrlicher?

## Strategisch gute Aenderungen

Strategisch gut sind typischerweise Aenderungen, die:

- Scope verkleinern statt vergroessern
- Wahrheit maschinenlesbarer machen
- Drift sichtbar machen
- Restore verifizierbarer machen
- Queue-, Retry- oder Cleanup-Pfade sicherer machen
- historische Nachvollziehbarkeit verbessern
- globale Operationen in dokument- oder workspace-scoped Prozesse zerlegen

## Strategisch schlechte Aenderungen

Strategisch schlecht sind typischerweise Aenderungen, die:

- Komfort ueber Determinismus stellen
- globale Mutation einfacher machen als begrenzte Mutation
- Beobachtbarkeit durch implizite Magie ersetzen
- neue operative Last erzeugen, ohne Recovery- oder Repair-Pfad
- Nachweise spaeter versprechen statt direkt einzuplanen
- einen gruenen Teilscope als Gesamtfreigabe verkaufen

## Review-Abschlussformel

Eine Aenderung passt strategisch nur dann, wenn sie die Frage beantwortet:

`Macht diese Aenderung das System langfristig verantwortbarer?`

Wenn die ehrlichste Antwort `nein`, `unklar` oder `nur mit viel Hoffnung` lautet, ist die Aenderung nicht freigabefertig.
