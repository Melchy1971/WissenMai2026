# Jira-Stories — Importcenter: Ordner-Import (Feature 1, Variante A / `webkitdirectory`)

**Projekt:** Wissensbasis V1 (Ruflo)
**Quelle:** Fachkonzept_Importcenter_Ordner_PST.md (E1 = Variante A entschieden)
**Stand:** 2026-06-30
**Abnahmemaßstab (global):** Abnahme erst bei fehlerfreiem Live-Lauf — kein Mock, kein Stub, reale Datei-/DB-Beteiligung.

---

## Struktur

- **Epic:** Importcenter — Ordner-Import (Variante A).
- **Enabler (ENB-*):** gemeinsamer Batch-Baustein, ohne den F1 nicht lauffähig ist. Auch Voraussetzung für PST (F2).
- **Fachlich (F1-S*):** ordnerspezifische Stories.
- Reihenfolge = Umsetzungsreihenfolge. ENB vor F1.

**Globale Definition of Done (gilt für jede Story zusätzlich zu den AK):**

- Live-Lauf gegen reale DB grün, kein Stub.
- Unit- + Integrationstests vorhanden und grün; Negativfälle abgedeckt.
- `log_import_event`/Korrelations-ID-Schema bedient.
- Keine technischen IDs/Pfade im UI geleakt (bestehendes Gate).
- Fehlertexte deutsch, fachlich verständlich.

---

## Epic

> **EPIC-IMP-FOLDER — Ordner-Import im Importcenter**
> Als Nutzer der Wissensbasis möchte ich einen kompletten Ordner per Mausklick auswählen und in einem Vorgang importieren, damit ich nicht jede Datei einzeln hochladen muss.
> Umfang: Variante A (`webkitdirectory`, Browser-Upload). Pfad-/Desktop-Variante ist nicht Teil dieses Epics (Phase 2).

---

## Enabler-Stories (Batch-Fundament)

### ENB-1 — Datenmodell `import_batch` / `import_batch_item`

> Als System möchte ich einen Import-Vorgang als Batch über N Elemente abbilden, damit Mengen-Importe mit Pro-Element-Status möglich sind.

**Akzeptanzkriterien**

```gherkin
Szenario: Batch- und Item-Tabellen existieren
  Gegeben die Alembic-Migration ist eingespielt
  Dann existiert Tabelle import_batch mit Feldern
       id, workspace_id, source_type, source_label, created_by, created_at,
       status, total_count, Zählerfelder je Item-Status, correlation_id
  Und existiert Tabelle import_batch_item mit Feldern
       id, batch_id (FK), relative_path, filename, mime_type, status,
       error_code, document_id (FK, nullable), content_hash (nullable)
  Und ein erfolgreiches Item referenziert genau ein document

Szenario: Item-Status ist auf den definierten Wertebereich beschränkt
  Gegeben ein import_batch_item
  Dann ist status aus {pending, running, succeeded, failed,
       skipped_unsupported, skipped_empty, skipped_duplicate, skipped_too_large}
```

**Abhängigkeiten:** keine. **Blockiert:** ENB-2..5, alle F1-S.

---

### ENB-2 — Batch-Upload-Eingang (Variante A)

> Als Frontend möchte ich einen Batch eröffnen, Dateien dazu hochladen und den Batch starten, damit ein Ordner mit vielen Dateien zuverlässig übertragen wird, ohne dass ein einzelner Sammel-Request in Timeouts läuft.

**Akzeptanzkriterien**

```gherkin
Szenario: Batch eröffnen
  Wenn POST /imports/folder mit source_label aufgerufen wird
  Dann wird ein import_batch im Status pending angelegt
  Und die batch_id wird zurückgegeben

Szenario: Datei mit Herkunftspfad hochladen
  Gegeben ein Batch im Status pending
  Wenn POST /imports/folder/{batch_id}/items mit Datei und webkitRelativePath aufgerufen wird
  Dann wird ein import_batch_item mit relative_path = webkitRelativePath angelegt
  Und die Originaldatei wird als Temp-Datei abgelegt

Szenario: Batch starten
  Gegeben ein Batch mit mindestens einem Item
  Wenn POST /imports/folder/{batch_id}/start aufgerufen wird
  Dann wechselt der Batch nach running
  Und die Verarbeitung der Items beginnt

Szenario: Datei über Pro-Datei-Limit wird serverseitig abgewiesen
  Wenn ein Item größer als max_upload_size_bytes (50 MB) hochgeladen wird
  Dann wird das Item mit Status skipped_too_large geführt
  Und der Batch bricht nicht ab
```

**Abhängigkeiten:** ENB-1.

---

### ENB-3 — Batch-Verarbeitung über bestehende Pipeline (Fan-out)

> Als System möchte ich jedes Item einzeln durch die bestehende Import-Pipeline schicken, damit kein Verarbeitungscode dupliziert wird und Teil-Erfolg möglich ist.

**Akzeptanzkriterien**

```gherkin
Szenario: Jedes Item durchläuft parse → ocr → normalize → hash → persist
  Gegeben ein gestarteter Batch mit gemischten Dateien
  Wenn die Verarbeitung läuft
  Dann wird jedes Item über die bestehende ImportService-Pipeline verarbeitet
  Und erfolgreiche Items erhalten ein document mit Status succeeded

Szenario: Einzelfehler bricht den Batch nicht ab
  Gegeben ein Batch mit einer fehlerhaften und mehreren gültigen Dateien
  Wenn die Verarbeitung läuft
  Dann wird die fehlerhafte Datei als failed mit error_code protokolliert
  Und alle gültigen Dateien werden erfolgreich importiert
  Und der Batch endet in completed_with_errors

Szenario: Nur Infrastrukturfehler bricht den Batch ab
  Gegeben die Datenbank ist während der Verarbeitung nicht erreichbar
  Dann wechselt der Batch nach failed
  Und der Fehler ist protokolliert
```

**Abhängigkeiten:** ENB-1, ENB-2.

---

### ENB-4 — Fortschritt / Status-Abfrage

> Als Nutzer möchte ich den Fortschritt eines laufenden Batches live sehen, damit ich bei langen Läufen einschätzen kann, wie weit der Import ist.

**Akzeptanzkriterien**

```gherkin
Szenario: Live-Zähler je Status
  Gegeben ein laufender Batch mit N Items
  Wenn GET /imports/folder/{batch_id} aufgerufen wird
  Dann werden total_count und die Zähler je Status zurückgegeben
  Und die Zähler werden pro verarbeitetem Item fortgeschrieben, nicht erst am Ende

Szenario: Endstatus korrekt
  Gegeben alle Items sind verarbeitet
  Dann ist der Batch-Status completed, completed_with_errors oder failed
       gemäß der Status-Regeln aus dem Fachkonzept (Abschnitt 5.2)
```

**Abhängigkeiten:** ENB-1, ENB-3.

---

### ENB-5 — Ergebnisbericht (persistiert)

> Als Nutzer möchte ich nach Abschluss einen vollständigen, später abrufbaren Bericht je Batch, damit ich nachvollziehen kann, was importiert, übersprungen oder fehlgeschlagen ist (Wissenssicherung).

**Akzeptanzkriterien**

```gherkin
Szenario: Bericht je Element
  Gegeben ein abgeschlossener Batch
  Wenn der Ergebnisbericht abgerufen wird
  Dann enthält er je Item: relative_path, filename, status, error_code/-text, document_id
  Und ein Aggregat: gesamt, succeeded, je skipped-Grund, failed

Szenario: Bericht überlebt die Sitzung
  Gegeben ein abgeschlossener Batch
  Wenn die Sitzung beendet und neu aufgerufen wird
  Dann ist der Bericht weiterhin abrufbar
```

**Abhängigkeiten:** ENB-1, ENB-3.

---

## Fachliche F1-Stories

### F1-S1 — Ordnerauswahl per Mausklick mit Frontend-Vorfilter

> Als Nutzer möchte ich per Mausklick einen Ordner wählen, damit alle enthaltenen unterstützten Dateien für den Import vorbereitet werden, ohne unnötige Dateien hochzuladen.

**Akzeptanzkriterien**

```gherkin
Szenario: Ordner rekursiv erfassen
  Gegeben ich klicke im Importcenter auf "Ordner importieren"
  Wenn ich im Browser-Dialog einen Ordner wähle
  Dann erfasst das Frontend alle Dateien inklusive Unterordner (webkitdirectory)
  Und zeigt den Ordnernamen an

Szenario: Vorfilter vor Upload
  Gegeben ein gewählter Ordner mit unterstützten und nicht unterstützten Typen
  Dann lädt das Frontend nur Dateien mit registriertem Parser (txt, md, docx, doc, pdf) hoch
  Und nicht unterstützte Dateien werden nicht übertragen, sondern im Vorab-Bericht als skipped_unsupported ausgewiesen
```

**Abhängigkeiten:** ENB-2.

---

### F1-S2 — Vorab-Prüfung vor dem Upload

> Als Nutzer möchte ich vor dem Start eine Übersicht sehen, damit ich Umfang und Upload-Volumen kenne und gezielt eingrenzen kann, bevor etwas übertragen wird.

**Akzeptanzkriterien**

```gherkin
Szenario: Übersicht anzeigen
  Gegeben ein gewählter Ordner
  Dann zeigt das System je Dateityp Anzahl und Gesamtgröße
  Und das resultierende Upload-Volumen
  Und Anzahl: unterstützt / nicht unterstützt / leer / zu groß / erkannte Duplikate

Szenario: Eingrenzen vor Start
  Gegeben die Übersicht
  Wenn ich einen Dateityp abwähle
  Dann aktualisiert sich das angezeigte Upload-Volumen entsprechend

Szenario: Kein Start ohne Bestätigung
  Gegeben die Übersicht ist angezeigt
  Dann startet kein Upload, bevor ich aktiv bestätige
```

**Abhängigkeiten:** F1-S1.

---

### F1-S3 — Herkunftspfad als Dokumentmetadatum

> Als Nutzer möchte ich am importierten Dokument den ursprünglichen relativen Pfad sehen, damit die Herkunft nachvollziehbar bleibt (Telekom-Wissenssicherung).

**Akzeptanzkriterien**

```gherkin
Szenario: relative_path wird gespeichert
  Gegeben eine Datei unterordner/a/bericht.pdf im Ordner-Import
  Wenn sie erfolgreich importiert ist
  Dann trägt das Dokument als Metadatum den relativen Pfad "unterordner/a/bericht.pdf"

Szenario: Unicode-Pfade normalisiert
  Gegeben ein Dateiname mit Umlauten (NFC/NFD-Varianten)
  Dann wird der relative Pfad in normalisierter Form gespeichert
  Und Dedup behandelt NFC/NFD-gleiche Pfade konsistent
```

**Abhängigkeiten:** ENB-3.

---

### F1-S4 — Dedup ohne Batch-Abbruch

> Als Nutzer möchte ich, dass inhaltsgleiche Dateien übersprungen statt als Fehler behandelt werden, damit Duplikate im Ordner den Import nicht stören.

**Akzeptanzkriterien**

```gherkin
Szenario: Duplikat gegen bestehendes Dokument
  Gegeben ein Dokument mit content_hash X existiert bereits im Workspace
  Wenn eine inhaltsgleiche Datei importiert wird
  Dann wird das Item als skipped_duplicate geführt
  Und es entsteht kein zweites Dokument
  Und der Batch läuft normal weiter

Szenario: Duplikat innerhalb desselben Batches
  Gegeben dieselbe Datei liegt in zwei Unterordnern
  Wenn der Ordner importiert wird
  Dann wird sie einmal importiert
  Und das zweite Vorkommen ist skipped_duplicate
  Und beide Pfade sind im Bericht protokolliert

Szenario: Erneuter Import desselben Ordners
  Gegeben ein Ordner wurde bereits vollständig importiert
  Wenn ich denselben Ordner erneut importiere
  Dann entstehen 0 neue Dokumente
  Und alle Items sind skipped_duplicate
```

**Abhängigkeiten:** ENB-3. **Hinweis:** nutzt bestehenden `UniqueConstraint(workspace_id, content_hash)`.

---

### F1-S5 — Skip-Klassen für nicht importierbare Dateien

> Als Nutzer möchte ich, dass leere, zu große und unbrauchbare Dateien klar klassifiziert übersprungen werden, damit der Bericht eindeutig ist.

**Akzeptanzkriterien**

```gherkin
Szenario: Leere Datei
  Wenn eine 0-Byte-Datei verarbeitet wird
  Dann ist das Item skipped_empty

Szenario: Zu große Datei
  Wenn eine Datei über 50 MB gewählt wird
  Dann erkennt das Frontend dies und überträgt sie nicht
  Und das Item ist skipped_too_large

Szenario: Nicht unterstützter Typ rutscht trotzdem durch
  Gegeben eine Datei mit unterstützter Endung aber nicht parsebarem Inhalt
  Dann ist das Item failed mit definiertem error_code
  Und der Batch läuft weiter
```

**Abhängigkeiten:** ENB-3, F1-S1.

---

### F1-S6 — Ausschlussliste für Systemdateien

> Als Nutzer möchte ich, dass technische Systemdateien automatisch ausgeschlossen werden, damit mein Wissensbestand nicht mit Müll gefüllt wird.

**Akzeptanzkriterien**

```gherkin
Szenario: Standard-Ausschluss aktiv
  Gegeben ein Ordner enthält .DS_Store, Thumbs.db, desktop.ini und einen .git-Ordner
  Wenn ich den Ordner wähle
  Dann werden diese Einträge weder hochgeladen noch importiert
  Und sie erscheinen nicht als Fehler

Szenario: Ausschlussliste konfigurierbar
  Gegeben die Ausschlussliste
  Dann kann sie über Konfiguration angepasst werden, ohne Codeänderung
```

**Abhängigkeiten:** F1-S1.

---

### F1-S7 — Mengen-Obergrenzen (Schutz vor Überlast)

> Als System möchte ich Ordner-Importe oberhalb definierter Grenzen vor dem Upload blockieren, damit weder Browser noch Backend in unkontrollierte Last laufen.

> ⚠️ Konkrete Grenzwerte hängen an Entscheidung **E2**. Default-Vorschlag bis dahin: 5.000 Dateien / 2 GB Upload-Volumen.

**Akzeptanzkriterien**

```gherkin
Szenario: Obergrenze überschritten
  Gegeben ein Ordner mit mehr als der erlaubten Dateianzahl oder Upload-Volumen
  Wenn ich ihn wähle
  Dann blockiert das System den Start mit klarem Hinweis und Empfehlung zur Aufteilung
  Und es wird keine Teilmenge "bis es bricht" hochgeladen

Szenario: Grenzwerte konfigurierbar
  Dann sind Dateianzahl- und Volumen-Grenze über Konfiguration setzbar
```

**Abhängigkeiten:** F1-S2. **Offen:** E2.

---

### F1-S8 — Batch abbrechen

> Als Nutzer möchte ich einen laufenden Ordner-Import abbrechen können, damit ich einen versehentlich gestarteten oder zu großen Lauf stoppen kann.

**Akzeptanzkriterien**

```gherkin
Szenario: Abbruch während der Verarbeitung
  Gegeben ein laufender Batch
  Wenn ich abbreche
  Dann wird das aktuell laufende Element sauber zu Ende geführt
  Und danach gestoppt
  Und der Batch-Status ist cancelled

Szenario: Bereits importierte Dokumente bleiben gültig
  Gegeben ein abgebrochener Batch
  Dann bleiben alle bis dahin erfolgreich importierten Dokumente erhalten
  Und es existieren keine halben/teilweisen Dokumente
```

**Abhängigkeiten:** ENB-3, ENB-4.

---

### F1-S9 — Fehlerbehandlung einzelner Elemente

> Als Nutzer möchte ich bei problematischen Einzeldateien einen klaren Fehler statt eines Abbruchs oder stillen Verschluckens, damit ich gezielt nacharbeiten kann.

**Akzeptanzkriterien**

```gherkin
Szenario: Nicht lesbare Datei
  Gegeben eine Datei kann nicht gelesen werden (gesperrt/Berechtigung)
  Dann ist das Item failed mit error_code read_denied
  Und der Batch läuft weiter

Szenario: Passwortgeschützte PDF/DOCX
  Gegeben eine passwortgeschützte Datei
  Dann ist das Item failed mit definiertem error_code
  Und es erfolgt kein stiller Skip

Szenario: Leere Auswahl ohne unterstützte Dateien
  Gegeben ein Ordner ohne importierbare Dateien
  Dann meldet das System dies klar
  Und es wird kein Batch gestartet
```

**Abhängigkeiten:** ENB-3.

---

## Umsetzungsreihenfolge

1. ENB-1 → ENB-2 → ENB-3 → ENB-4 → ENB-5 (Fundament)
2. F1-S1 → F1-S2 (Auswahl + Vorab-Prüfung)
3. F1-S3, F1-S4, F1-S5, F1-S6 (Verarbeitungsregeln)
4. F1-S7 (Grenzen, sobald E2 entschieden), F1-S8, F1-S9

## Abhängigkeit zu PST (F2)

ENB-1..5 sind identisch für PST nutzbar. F2 ergänzt nur einen PST-/E-Mail-Parser und die Fan-out-Logik PST → Items. Die Enabler hier nicht ordnerspezifisch bauen.
