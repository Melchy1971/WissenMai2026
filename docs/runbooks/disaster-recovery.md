# Disaster Recovery Runbook

Stand: 2026-05-11

## Zweck

Dieses Runbook beschreibt die operative Wiederherstellung fuer schwere Stoerungsfaelle im lokalen produktionsnahen M4e-Betrieb.

Es ergaenzt das allgemeine Backup/Restore-Runbook in [docs/runbooks/backup-restore.md](H:/WissenMai2026/docs/runbooks/backup-restore.md) um konkrete Disaster-Recovery-Szenarien, Operator-Schritte und Checklisten.

## Operator Guide

Grundregeln fuer alle DR-Szenarien:

- zuerst Stoerungsbild eingrenzen, dann mutierende Schritte ausfuehren
- nie auf der einzigen verbliebenen Sicherung arbeiten
- Backup immer vor einem destruktiven Eingriff validieren
- Restore immer gegen leere oder bewusst vorbereitete Zielumgebung ausfuehren
- nach Restore immer Reindex, Drift-Check und `postgres_truth`-Smoke-Subset laufen lassen
- alle Ergebnisse schriftlich festhalten: Zeitpunkt, verwendetes Backup, Zielumgebung, Abweichungen

Standard-Werkzeuge:

- `python -m app.cli backup validate --input <path>`
- `python -m app.cli backup restore --input <path>`
- `python -m app.cli search rebuild-index`
- PostgreSQL-Zugriff fuer DB-Reset, DB-Erreichbarkeit und SQL-Stichproben

Standard-Validierung nach Recovery:

- Dokumente lesbar
- Search liefert erwartete Treffer
- Chat Retrieval liefert konsistente Citations
- Lifecycle-Zustaende stimmen
- Historical Citations bleiben lesbar und tragen korrekten `source_status`
- Queue-Zustaende sind konsistent
- Drift-Check ist `ok`
- `postgres_truth`-Smoke-Subset ist gruen

## Szenario 1: Datenbank zerstoert

### Symptome

- Backend startet nicht oder liefert DB-Fehler
- `alembic current` oder einfache SQL-Verbindung schlagen fehl
- Dokumentlisten, Search, Chat und Auth fallen gleichzeitig aus

### Recovery-Schritte

1. Applikation stoppen oder in ruhigen Betriebszustand bringen.
2. Letztes gueltiges Backup identifizieren.
3. `python -m app.cli backup validate --input <path>` ausfuehren.
4. Ziel-Datenbank neu erzeugen oder leeren.
5. `python -m app.cli backup restore --input <path>` ausfuehren.
6. Ergebnis der Restore-Pipeline auf Config-Check, Reindex, Drift-Check und Truth-Smoke pruefen.

### Validierung

- DB-Verbindung wieder moeglich
- Dokumentanzahl entspricht Erwartung aus Manifest oder Quellsystem
- Search und Chat laufen wieder
- Lifecycle- und Citation-Zustaende sind konsistent

### Risiken

- falsches Backup gewaehlt
- Restore in nicht leere DB fuehrt zu Vermischung
- lokale Konfiguration passt nicht mehr zum Snapshot

### Dauer

- niedrig bis mittel, typischerweise 15-45 Minuten bei vorhandenem Backup und erreichbarer Ziel-DB

### Datenverlust-Risiko

- mittel, abhaengig vom Abstand zwischen letztem gueltigen Backup und Ausfallzeitpunkt

### Checkliste

- [ ] Backup validiert
- [ ] Ziel-DB leer oder neu erzeugt
- [ ] Restore erfolgreich
- [ ] Drift-Check `ok`
- [ ] `postgres_truth`-Smoke gruen

## Szenario 2: Upload-Dateien beschaedigt

### Symptome

- Originaldateien fehlen oder sind unlesbar
- Re-Import oder technische Rekonstruktion aus Datei-Artefakten scheitert
- Dokumente sind ggf. noch in DB sichtbar, aber Datei-Referenzen brechen

### Recovery-Schritte

1. Betroffene Dateien und betroffenen Workspace eingrenzen.
2. Letztes gueltiges Backup mit intakten `files/`-Artefakten identifizieren.
3. Backup validieren.
4. Wenn nur Dateien betroffen sind: technische Originaldatei-Kopien aus `backup/files/` gezielt wiederherstellen.
5. Falls DB-Metadaten ebenfalls inkonsistent sind: vollstaendigen Restore ausfuehren.
6. Search-Rebuild ausfuehren, falls Datei-/Chunk-Rekonstruktion betroffen war.

### Validierung

- referenzierte Originaldateien sind wieder vorhanden
- betroffene Dokumente bleiben lesbar
- Reindex laeuft erfolgreich

### Risiken

- Teilrestore auf falschen Dateibestand
- Dateistand und DB-Metadaten laufen auseinander

### Dauer

- niedrig bis mittel, typischerweise 10-30 Minuten bei reinem Datei-Teilrestore

### Datenverlust-Risiko

- niedrig bis mittel, solange aktuelle Datei-Artefakte in einem gueltigen Backup enthalten sind

### Checkliste

- [ ] betroffene Dateien identifiziert
- [ ] Dateiartefakte aus Backup wiederhergestellt
- [ ] Referenzen pruefbar vorhanden
- [ ] Search/Reindex erfolgreich falls noetig

## Szenario 3: Search Index verloren

### Symptome

- Search liefert keine oder falsche Treffer
- Drift- oder Inconsistency-Checks schlagen an
- Dokumente und Chunks sind in der DB vorhanden, aber Retrieval ist inkonsistent

### Recovery-Schritte

1. DB-Bestand und Dokumentzahlen pruefen.
2. `python -m app.cli search rebuild-index` ausfuehren.
3. Falls Search weiterhin inkonsistent ist: Backup validieren und Restore-Pipeline ausfuehren.
4. Drift-Check erneut auswerten.

### Validierung

- erwartete Suchtreffer erscheinen wieder
- Drift-Check ist `ok`
- Chat Retrieval liefert konsistente aktive Quellen

### Risiken

- zugrunde liegender DB-Schaden wird als reiner Indexfehler fehlgedeutet
- Lifecycle-Fehler bleiben trotz Reindex bestehen, wenn Quelldaten bereits inkonsistent sind

### Dauer

- niedrig, typischerweise 5-15 Minuten

### Datenverlust-Risiko

- niedrig, da der Search-Index rekonstruiert wird und kein primaeres Backup-Artefakt ist

### Checkliste

- [ ] DB-Bestand plausibel
- [ ] Reindex erfolgreich
- [ ] Drift-Check `ok`
- [ ] Search-/Retrieval-Stichprobe erfolgreich

## Szenario 4: Queue inkonsistent

### Symptome

- Jobs bleiben in `running`, `retryable` oder `dead_letter` haengen
- Uploads oder Rebuilds kommen nicht mehr voran
- Queue-Status passt nicht zu sichtbarem Dokumentzustand

### Recovery-Schritte

1. Betroffene Jobs und Status per SQL oder Diagnostics eingrenzen.
2. Pruefen, ob ein reiner Betriebsfehler ohne Datenverlust vorliegt.
3. Wenn die DB konsistent ist: Queue-Zustaende gezielt stabilisieren oder aus Backup/Restore-Pipeline neu aufbauen.
4. Falls Queue- und Dokumentzustand auseinanderlaufen: vollstaendigen Restore auf leere Zielumgebung ausfuehren.
5. `postgres_truth`-Smoke-Subset mit Queue-relevanten Checks auswerten.

### Validierung

- keine unerwartet haengenden Jobs
- Queue-Status stimmt mit dokumentiertem Objektzustand ueberein
- Upload- oder Rebuild-Nachfolgepfade funktionieren wieder

### Risiken

- manuelle Queue-Eingriffe ohne klares Truth-Bild
- Replay oder Cleanup auf falschem Job

### Dauer

- mittel, typischerweise 15-45 Minuten

### Datenverlust-Risiko

- mittel, wenn Queue-Zustand und Dateisystem/DB bereits auseinanderlaufen

### Checkliste

- [ ] betroffene Jobs identifiziert
- [ ] Queue-Zustand fachlich bewertet
- [ ] Restore oder Stabilisierung ausgefuehrt
- [ ] Queue-Konsistenz validiert

## Szenario 5: Teilweiser Restore

### Symptome

- nur ein Teil des Systems ist betroffen
- DB lebt, aber einzelne Artefakte oder Teilbereiche fehlen
- ein Vollrestore waere unverhaeltnismaessig riskant oder unnötig

### Recovery-Schritte

1. Schaden sauber auf DB, Dateien oder Index begrenzen.
2. Backup validieren.
3. Nur den betroffenen Teilbereich wiederherstellen, wenn der Restzustand nachweisbar konsistent bleibt.
4. Reindex und Drift-Check ausfuehren.
5. Wenn Teilrestore Inkonsistenzen erzeugt: auf Vollrestore wechseln.

### Validierung

- betroffener Teilbereich wieder funktionsfaehig
- keine neuen orphaned Daten
- Search und Retrieval im betroffenen Scope konsistent

### Risiken

- Teilrestore erzeugt versteckte Inkonsistenzen
- Daten- und Dateistand stammen aus unterschiedlichen Sicherungszeitpunkten

### Dauer

- niedrig bis mittel, typischerweise 10-30 Minuten

### Datenverlust-Risiko

- mittel, wenn Teilrestore ohne harte Konsistenzpruefung erfolgt

### Checkliste

- [ ] Schaden isoliert
- [ ] Teilrestore bewusst begrenzt
- [ ] Drift-Check `ok`
- [ ] keine orphaned Daten sichtbar

## Szenario 6: Vollstaendiger Server-Neuaufbau

### Symptome

- Host ist verloren, unbrauchbar oder bewusst neu aufzusetzen
- Applikation, Datenbankzugang und Dateistand muessen komplett neu bereitgestellt werden

### Recovery-Schritte

1. Neue Zielumgebung mit benoetigten Runtime-Abhaengigkeiten bereitstellen.
2. PostgreSQL-Zielinstanz und Dateisystem-Root vorbereiten.
3. Konfiguration auf Basis des Backup-Snapshots herstellen.
4. Repository oder Release-Stand bereitstellen.
5. `python -m app.cli backup validate --input <path>` ausfuehren.
6. `python -m app.cli backup restore --input <path>` ausfuehren.
7. Backend und Frontend starten.
8. Such-, Chat-, Lifecycle- und Queue-Stichproben durchfuehren.

### Validierung

- System startet auf neuem Host
- Login funktioniert
- Dokumente, Search und Chat funktionieren
- Lifecycle- und Citation-Zustaende stimmen
- Queue ist konsistent

### Risiken

- fehlende Systemabhaengigkeiten auf neuem Host
- falsche Konfigurationsuebernahme
- Restore auf nicht kompatibler PostgreSQL-Umgebung

### Dauer

- mittel bis hoch, typischerweise 30-120 Minuten je nach Host-Bereitstellung

### Datenverlust-Risiko

- mittel, primaer abhaengig von Backup-Aktualitaet und korrekter Konfigurationsrekonstruktion

### Checkliste

- [ ] Zielhost vorbereitet
- [ ] PostgreSQL erreichbar
- [ ] Konfiguration aus Snapshot uebernommen
- [ ] Restore erfolgreich
- [ ] Login/Search/Chat/Lifecycle/Queue validiert

## Globale Validierungs-Checkliste nach jeder Recovery

- [ ] Dokumentanzahl plausibel
- [ ] Chunkanzahl plausibel
- [ ] Dokumente lesbar
- [ ] Search funktioniert
- [ ] Chat Retrieval funktioniert
- [ ] Historical Citations lesbar und `source_status` korrekt
- [ ] Lifecycle korrekt
- [ ] Queue konsistent
- [ ] keine offensichtlichen orphaned Daten
- [ ] Drift-Check `ok`
- [ ] `postgres_truth`-Smoke-Subset gruen

## Globale Eskalationsregeln

- Auf Vollrestore wechseln, wenn ein Teilrestore Drift oder orphaned Daten erzeugt.
- Kein manuelles Greenlighting ohne Drift-Check und Truth-Smoke.
- Kein Recovery-Abschluss bei ungepruefter Konfigurationsabweichung.