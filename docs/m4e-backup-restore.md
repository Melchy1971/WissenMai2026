# M4e - Backup- und Restore-Konzept

Stand: 2026-05-05

## Realer Status am 2026-05-11

- Dieses Dokument beschreibt weiterhin das Zielbild, aber nicht mehr nur ein reines Konzept.
- Im aktuellen Repository gibt es nun einen nachweisbaren CLI-first Codepfad fuer `backup create`, `backup validate`, `backup restore` und `search rebuild-index`.
- Der Datenbankteil des Backups wird im Minimalpfad als PostgreSQL-SQL-Dump ueber `pg_dump` erzeugt.
- Technische Originaldatei-Kopien werden im Importpfad persistiert und in den Versions-Metadaten referenziert.
- Es gibt fokussierte Unit-Tests fuer Dateiablage, Backup-Validierung und Restore-Orchestrierung.
- Ein praktischer Restore-Nachweis gegen eine leere reale lokale PostgreSQL-Ziel-DB ist erfolgt.
- M4e ist deshalb fachlich definiert und technisch `partial` mit realem Minimal-Nachweis, aber noch nicht freigabefaehig abgeschlossen.
- Vor M5 wird nur ein manueller Minimal-Scope verlangt, kein voll ausgebauter Backup-Stack.

## Go/No-Go vor M5

Entscheidung:

- M4e ist **vor M5 im Minimal-Scope erforderlich**.
- M4e ist **nicht** als voll ausgebautes Betriebs- oder Cloud-Backup-Thema vor M5 erforderlich.

Begruendung:

- M5 baut auf einem lokalen Wissenssystem auf, das Auth, Upload, Lifecycle, Chat und Suchzustand produktionsnah betreibt.
- Ohne manuellen Restore-Nachweis bleibt ein lokaler Bedien-, DB- oder Host-Fehler irreversibel.
- Fuer einen lokalen Produktpfad ist das kein spaeterer Komfortpunkt, sondern ein Mindestschutz gegen Totalausfall.
- Gleichzeitig wuerde ein Vollausbau mit Scheduler, Cloud-Zielen, Inkrementen oder Schluesselverwaltung M4 unnoetig verbreitern.

Daraus folgt:

- **Go vor M5** nur mit M4e-Minimal-Scope.
- **No-Go vor M5** fuer erweitertes Backup-Produktisieren ausserhalb dieses Minimal-Scope.

## Finaler M4e Minimal-Scope vor M5

Ziel:

- M4e soll operative Wiederherstellung ermoeglichen.
- M4e soll vor M5 keinen Enterprise-Backup-Stack bauen.

In Scope:

- PostgreSQL-DB-Dump als primaeres Datenbankartefakt des Minimal-Backups
- technische Originaldatei-Kopien der importierten Quelldateien
- Konfigurationsartefakt fuer die lokale Wiederherstellung
- Restore auf eine leere Zielumgebung
- Reindex nach Restore als Pflichtschritt
- Wiederherstellung der folgenden Datenklassen:
  - Dokumente
  - Versionen
  - Chunks
  - Chat-Sessions
  - Citations
  - Queue-Jobs

Minimaler Betriebszuschnitt:

- manuell ausloesbarer Backup-Pfad
- manuell ausfuehrbarer Restore-Pfad auf leere Ziel-Datenbank
- kein Zwang zu Web-UI oder mutierender Admin-API
- kein Zwang zu periodischer Automatisierung in M4e-Minimal

## Expliziter Nicht-Scope vor M5

- inkrementelle Backups
- Multi-Region-Backup oder Multi-Region-Restore
- automatische Cloud-Replikation
- Zero-Downtime-Restore
- Point-in-Time-Recovery
- verschluesselte Backupverwaltung als eigenes Produktisierungsthema
- Aufbewahrungs- und Rotationssysteme
- mandantenuebergreifende Backup-Orchestrierung
- vollautomatischer Restore ueber Web-API

## Gate-Regeln fuer M4e-Minimal

Alle Bedingungen muessen gleichzeitig erfuellt sein:

- Ein Backup ist manuell erzeugbar und enthaelt PostgreSQL-DB-Dump, Originaldatei-Artefakte, Konfiguration und Manifest.
- Ein Restore auf eine leere Zielumgebung ist per Runbook erfolgreich durchfuehrbar.
- Nach Restore ist `alembic upgrade head` erfolgreich.
- Der Search-Index ist nach Restore neu aufbaubar; Reindex ist Pflicht und kein optionaler Komfortschritt.
- Die Wiederherstellung der Minimal-Datenklassen ist praktisch nachweisbar: Dokumente, Versionen, Chunks, Chat-Sessions, Citations und Queue-Jobs.
- Der Restore-Nachweis ist nicht nur beschrieben, sondern vollstaendig praktisch gegen eine leere Ziel-DB durchgefuehrt.
- `postgres_truth` ist nach Restore erneut gruen: `passed = collected`, `failed = 0`, `errors = 0`, `skipped = 0`, `exit_code = 0`.

## Ziel

M4e stellt sicher, dass das lokale Wissenssystem bei Datenbankfehlern, Dateisystemfehlern oder Bedienfehlern nicht irreversibel verloren geht. Die Wiederherstellung muss fuer den gesamten aktiven Workspace-Bestand nachvollziehbar und validierbar sein.

Der Fokus liegt auf einem lokalen, produktionsnahen Betrieb mit klarer Restore-Faehigkeit, nicht auf verteilter Hochverfuegbarkeit.

## Grundsatzentscheidung

Das heutige System verwirft Originaldateien nach dem Import. Damit ist ein vollstaendiges Backup gemaess M4e derzeit technisch nicht moeglich.

M4e fuehrt deshalb eine neue Produktisierungsregel ein:

- Originaldateien duerfen optional als technische Backup-Kopie gespeichert werden.
- Diese Kopie ist nicht die fachlich fuehrende Quelle.
- Fachlich fuehrend bleiben weiterhin:
  - `documents`
  - `document_versions.normalized_markdown`
  - `document_chunks`

Die Backup-Kopie dient ausschliesslich:

- dem Disaster Recovery,
- der Integritaetspruefung,
- der Rekonstruktion von Chunks und Search-Index,
- dem spaeteren Re-Import bei Parser- oder Migrationsaenderungen.

## Zu sichernde Bestandteile

Pflichtbestandteile eines M4e-Minimal-Backups vor M5:

- Datenbank
- hochgeladene Originaldateien als technische Backup-Kopie
- Konfiguration

Nicht primaer sicherungspflichtig, sondern rekonstruierbar:

- Search-Index

### 1. Datenbank

Enthaelt mindestens:

- Dokumente
- Versionen
- Chunks
- Chat- und Citation-Persistenz
- Auth-, Workspace- und Lifecycle-Zustaende ab M4a/M4c
- Import- und Betriebsmetadaten

Backup-Einheit:

- finaler Minimal-Scope: PostgreSQL-DB-Dump als Datenbankartefakt
- bis zur vollstaendigen Umstellung bleibt der aktuelle `table-json`-Pfad ein technischer Zwischenstand und noch nicht die finale Zieldefinition

Praktischer Nachweis am 2026-05-11:

- lokales Backup erfolgreich erzeugt
- Backup erfolgreich validiert
- Ziel-DB auf leeren Schema-Zustand gebracht
- Restore gegen lokale PostgreSQL-Ziel-DB erfolgreich durchgefuehrt
- `alembic upgrade head` als Restore-Vorbereitung erfolgreich
- Reindex ist im Restore-Codepfad enthalten; die separate Ausgabebestaetigung bleibt noch zu schaerfen

### 2. Originaldateien

Zukuenftiger Speicherort fuer M4e:

- dedizierter, nicht-oeffentlicher Storage-Pfad unter einer konfigurierten Backup-/Blob-Root

Anforderungen:

- keine Nutzung als Live-Serving-Quelle in der GUI
- keine direkte Auslieferung durch die Read-API
- Ablage unter stabiler ID-Struktur, nicht unter frei gewaehlt sichtbaren Dateinamen
- jede Datei referenziert genau einen technischen Speicherbeleg mit Hash

Empfohlene Ablageform:

- `blob_store/<workspace_id>/<document_id>/<content_hash>/<original_filename>`

### 3. Konfiguration

Zu sichern:

- `.env`-nahe Laufzeitkonfiguration oder dedizierte App-Konfigurationsdatei
- Backup-/Storage-Konfiguration
- Parser-relevante Systemkonfiguration, soweit lokal definiert

Nicht im Backup-Paket enthalten sein duerfen:

- unredigierte Secrets im Klartext ausserhalb des bewusst gesicherten Konfigurationsartefakts
- lokale Cache-Verzeichnisse
- temporaere Arbeitsdateien

### 4. Search-Index

Der Search-Index ist in M4e kein primaeres Sicherungsobjekt, sondern rekonstruierbar.

Begruendung:

- Suchvektoren lassen sich aus dem DB-Bestand und den persistierten Chunks neu aufbauen.
- Ein defekter oder fehlender Index darf Restore nicht blockieren.

## Backup-Strategie

## 1. Manuelles Backup

Zweck:

- bewusste Sicherung vor Upgrades, Migrationen, Parser-Wechseln oder groesseren Betriebsarbeiten

Ausloeser:

- CLI-Befehl
- optional spaeter Admin-Aktion in M4d, aber nicht primaer in M4e erforderlich

Pflichtverhalten:

- atomar gedachte Sicherung von DB-Dump, Dateiarchiv-Metadaten und Konfiguration
- Manifest-Datei mit Checksummen und Metadaten erzeugen
- Backup endet nur mit `success`, wenn alle Pflichtbestandteile geschrieben und validiert wurden

## 2. Periodisches Backup

Zweck:

- regelmaessige lokale Absicherung ohne manuelle Interaktion

Status in M4e:

- optional
- empfohlene Umsetzung ueber lokalen Scheduler, nicht ueber einen dauerhaft laufenden App-Worker

Beispiele:

- Windows Aufgabenplanung
- Systemd Timer oder Cron auf Linux

Empfehlung:

- taegliches Vollbackup
- zusaetzlich manuelles Backup vor Migrationen und Releases

## 3. Backup-Format

Empfohlenes Format:

- ein versionsiertes Backup-Verzeichnis oder ein einzelnes Archivpaket pro Lauf

Aktueller Implementierungsstand:

```text
backup-2026-05-11T14-30-00Z/
  manifest.json
  checksums.json
  db/
    database.sql
    pg_dump_version.txt
  files/
    <workspace_id>/<document_id>/<content_hash>/<original_filename>
  config/
    app-config.json
```

Manifest-Inhalt:

- `backup_format_version`
- `created_at`
- `app_version`
- `alembic_revision`
- `database_dump_format`
- `database_dump_path`
- `pg_dump_version`
- `pg_dump_version_path`
- `workspace_count`
- `document_count`
- `logical_components`
- `file_count`
- `config_files`
- `search_index_included`
- `original_file_root`

Empfehlung:

- Format zunaechst als Verzeichnis mit klaren Dateien, nicht als proprietaeres Binary-Format
- optional zusaetzlich komprimiertes `.zip` oder `.tar.gz` als Transportartefakt

## Restore-Strategie

## 1. Vollstaendiger Restore

Restore-Ziel:

- vollstaendige Wiederherstellung von Datenbank, referenzierten Originaldateien und Konfiguration in eine saubere Zielumgebung

Grundsatz:

- Restore erfolgt nie blind ueber eine laufende produktive Instanz ohne Vorpruefung
- bevorzugt zuerst in eine saubere Zielumgebung oder mit Wartungsmodus

Restore-Reihenfolge:

1. Applikation in Wartungsmodus oder offline nehmen.
2. Zielpfade fuer Datenbank, File Store und Konfiguration vorbereiten.
3. Manifest und Checksummen pruefen.
4. Datenbank-Dump einspielen.
5. Originaldateien in den technischen Storage-Pfad wiederherstellen.
6. Konfiguration wiederherstellen oder mappen.
7. Datenbankmigrationen gegen den wiederhergestellten Stand auf `head` ausfuehren.
8. Integritaetspruefung ausfuehren.
9. Search-Index neu aufbauen.
10. Applikation freigeben.

## 2. Integritaetspruefung nach Restore

Pflichtpruefungen:

- Manifest vollständig und lesbar
- alle deklarierten Dateien vorhanden
- alle Checksummen korrekt
- Datenbank erreichbar
- Alembic-Revision lesbar
- alle referenzierten Originaldateien im Blob-Store vorhanden
- jede aktuelle Dokumentversion hat rekonstruierbare Chunks oder bereits persistierte Chunks
- Search-Index-Refresh erfolgreich abgeschlossen Quelle: `reports/current/masterplan_status.json`.

Fachliche Pruefungen:

- Anzahl Dokumente im Backup entspricht dem Restore-Ergebnis
- Anzahl Versionen und Chunks stimmt
- dokumentierte Datei-Referenzen sind vollstaendig
- Chat-Citations referenzieren weiterhin existente `document_id` und `chunk_id`

## 3. Migration nach Restore

Regel:

- ein Restore darf nicht auf einer alten DB-Revision stehen bleiben
- nach Einspielen des Dumps wird stets `alembic upgrade head` ausgefuehrt

Begruendung:

- Backup-Artefakte koennen auf einem aelteren App-Stand entstanden sein
- Restore muss auf den aktuell unterstuetzten Schema-Stand gehoben werden

Sicherheitsregel:

- Migrationslauf ist Teil des Restore-Prozesses und nicht optional

## Validierung

### 1. Backup enthaelt alle referenzierten Dateien

Validierungsregel:

- fuer jede in der Datenbank registrierte technische Originaldatei existiert genau ein Backup-Artefakt mit passendem Hash

Erwarteter Nachweis:

- Manifest-Check plus Dateisystem-Check plus Hashvergleich

### 2. Chunks sind rekonstruierbar

Validierungsregel:

- aus `document_versions.normalized_markdown` muessen Chunks deterministisch neu berechnet werden koennen
- alternativ aus wiederhergestellter Originaldatei plus Parser/Normalizer, falls gezielt Re-Import validiert wird

Praktischer Nachweis fuer M4e:

- Sampling-Test fuer definierte Dokumente: gespeicherte Chunks gegen neu berechnete Chunk-Grenzen pruefen

### 3. Search-Index ist neu baubar

Validierungsregel:

- nach Restore kann ein Reindex-Lauf aus DB und Chunks erfolgreich erzeugt werden
- Suchabfragen auf bekannte Testdaten liefern danach wieder Treffer

## CLI- und API-Vorschlag

## CLI

Aktuelle erste Schnittstelle:

- `python -m app.cli backup create --output <path>`
- `python -m app.cli backup validate --input <path>`
- `python -m app.cli backup restore --input <path>`
- `python -m app.cli search rebuild-index`

Empfohlene weitere Entwicklung:

- CLI zuerst, weil Backup/Restore ein Betriebsprozess und keine normale Endnutzerfunktion ist

Optionale Flags:

- `--include-files`
- `--include-config`
- `--skip-search-rebuild`
- `--dry-run`
- `--json`

Erwartetes Verhalten:

- maschinenlesbarer Exit-Code
- kompaktes JSON-Summary fuer Automatisierung
- kein stilles Ueberspringen fehlender Bestandteile

## API

Fuer M4e nur optional und nachrangig:

- `POST /api/v1/admin/backups`
- `POST /api/v1/admin/backups/validate`
- `POST /api/v1/admin/search/rebuild-index`

Explizit nicht empfohlen fuer M4e:

- vollstaendiger Restore ueber die normale Web-API

Begruendung:

- Restore ist ein risikoreicher Betriebsprozess mit Wartungsmodus und Dateisystemzugriff
- dieser Prozess ist ueber CLI oder Runbook robuster als ueber einen Standard-HTTP-Request

## Risiken

### 1. Architekturbruch gegen bisherigen V1-Scope

Die Einfuehrung technischer Originaldatei-Kopien weicht die bisherige Regel `Originaldateien werden nicht gespeichert` auf.

Gegenmassnahme:

- explizit als M4e-Produktisierungsentscheidung dokumentieren
- Originaldatei-Kopie nicht als fachlich fuehrende Quelle behandeln

### 2. Unvollstaendige Datei-Backups

Risiko:

- Datenbank referenziert Dateien, die im Backup fehlen

Gegenmassnahme:

- Manifest plus Hashvalidierung als Pflichtschritt
- Backup bei fehlenden Dateien als fehlgeschlagen markieren

### 3. Restore auf inkonsistentem Schema-Stand

Risiko:

- DB-Dump und laufender App-Stand passen nicht zusammen

Gegenmassnahme:

- Restore immer mit anschliessendem `alembic upgrade head`

### 4. Falsche Sicherheitsannahmen bei Konfiguration

Risiko:

- Konfigurationsbackup enthaelt Geheimnisse oder umgebungsspezifische Pfade

Gegenmassnahme:

- Konfigurationsartefakte bewusst markieren
- Restore-Mapping fuer umgebungsspezifische Werte vorsehen

### 5. Search-Index wird als primaere Wahrheit behandelt

Risiko:

- Restore wird unnoetig fragil, wenn Indexdateien Pflicht werden

Gegenmassnahme:

- Search-Index ausdruecklich als rekonstruierbar definieren

### 6. Kein regelmaessiger Restore-Test

Risiko:

- Backups existieren, aber Restore funktioniert im Ernstfall nicht

Gegenmassnahme:

- periodischer Restore-Test in Testumgebung als spaetere Betriebsanforderung

## Akzeptanzkriterien

- Ein manuelles Minimal-Backup erzeugt DB-Dump, Datei-Backup, Konfigurationsartefakt und Manifest.
- Ein Restore auf leere Ziel-Datenbank kann den benoetigten Systemzustand wiederherstellen.
- Nach Restore laufen Migrationen auf `head`.
- Alle referenzierten Backup-Dateien sind vorhanden und geprueft.
- Chunks sind aus Persistenz oder Reimportpfad rekonstruierbar.
- Search-Index kann ohne Original-Indexdateien neu aufgebaut werden.
