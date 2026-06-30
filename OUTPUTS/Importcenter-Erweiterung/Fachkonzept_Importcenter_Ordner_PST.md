# Fachkonzept — Importcenter-Erweiterung: Ordner-Import & Outlook-PST-Import

**Projekt:** Wissensbasis V1 (Ruflo)
**Autor:** Markus Dickscheit (PO)
**Stand:** 2026-06-30
**Status:** Entwurf zur Abstimmung — E1 entschieden (Variante A, `webkitdirectory`); weitere offene Entscheidungen in Abschnitt 10
**Abnahmemaßstab:** Abnahme erst bei fehlerfreiem Live-Lauf (kein Mock, kein Stub).

---

## 1. Ist-Stand (codebasiert, nicht angenommen)

Belegt aus dem Backend (`backend/app/`):

- Import-Eingang: `POST /documents/import`, **genau eine** `UploadFile` pro Request (multipart).
- Größenlimit: `max_upload_size_bytes = 50 MB` (`core/config.py`).
- Verarbeitung asynchron: Upload → Temp-Datei → `enqueue_import_job` → Background-Job.
- Pipeline (`import_service.py`): `parse → ocr → normalize (Markdown) → hash → persist`.
- Registrierte Parser (`parser_service.py`): `text/plain`, Markdown, DOCX, DOC (via LibreOffice), PDF. **Kein** E-Mail-, EML-, MSG- oder PST-Parser.
- Kanonische Quelle: **Markdown**. Originaldatei ist laut README **nicht** fachlich führend.
- Dedup: `UniqueConstraint("workspace_id", "content_hash")` auf `documents` — identischer Inhalt pro Workspace ist nur einmal zulässig.
- **Kein** Batch-/Mehrfach-Job-Modell vorhanden: Datenmodell ist heute strikt `1 Upload = 1 Job = 1 Dokument`.
- Deployment laut README: „lokale GUI" (React/Vite) mit remote PostgreSQL, Single-User, V1 ohne Auth. Installer/Desktop-Paketierung ist als „Phase 2 (gesperrt)" vermerkt (`Entwicklung.md`).

**Konsequenz:** Beide neuen Importwege sind keine Parameter-Erweiterung des bestehenden Endpunkts, sondern verlangen einen neuen Baustein (Abschnitt 5) plus je einen Adapter (Abschnitt 6 und 7).

---

## 2. Scope

In Scope:

1. **Ordner-Import** — ein gesamter Ordner (rekursiv) wird in einem Vorgang importiert.
2. **Outlook-PST-Import** — eine `.pst`-Datei wird zerlegt; jede E-Mail (und optional jeder Anhang) wird zu einem oder mehreren Dokumenten.

Querschnitt für beide:

3. **Batch-Import-Modell** — ein Quell-Vorgang erzeugt N Dokumente mit Pro-Element-Status, Teil-Erfolg und aggregiertem Fortschritt.

Out of Scope: siehe Abschnitt 11.

---

## 3. Kritische Vorab-Entscheidungen (Sparring)

Diese Punkte sind keine Detailfragen, sondern Weichenstellungen. Ohne Entscheidung ist das Konzept nicht umsetzbar.

### 3.1 „Pfad per Mausklick" — entschieden: Variante A (`webkitdirectory`)

Die ursprüngliche Formulierung „den Pfad des Ordners per Mausklick wählen" hätte einen **absoluten Dateisystempfad** im Backend vorausgesetzt. Das gibt eine Browser-GUI aus Sicherheitsgründen nicht her. **Entscheidung E1: Variante A.**

- **Variante A — `webkitdirectory` (gewählt):** Der Nutzer wählt per Mausklick im Datei-Dialog einen Ordner. Der Browser sammelt **alle enthaltenen Dateien** (rekursiv) und lädt sie als Upload hoch. Das Backend erhält **keinen Pfad**, sondern eine Dateiliste mit relativen Pfaden (`webkitRelativePath`).

Direkte Konsequenzen dieser Wahl, die das Konzept prägen:

- Es gibt **keinen** server-lesbaren Pfad. „Pfad anzeigen" im UI = der vom Browser gemeldete Ordnername plus relative Pfade je Datei, nicht ein OS-Pfad.
- Der **gesamte** Ordnerinhalt geht über die Leitung. Upload-Volumen und -Dauer sind das zentrale Mengenrisiko (→ Obergrenzen E2, Vorab-Prüfung Abschnitt 4).
- Der bestehende Endpunkt nimmt **eine** `UploadFile`. Für Variante A ist ein **neuer Batch-Upload-Eingang** nötig (Abschnitt 6.1.1).
- Keine Ordner-Überwachung / Re-Synchronisation möglich (kein persistenter Pfad). Bewusst out of scope (Abschnitt 11).
- Die Pfad-/Desktop-Variante (vormals B) ist nicht gestrichen, sondern auf die geplante Phase-2-Desktop-Hülle verschoben (Abschnitt 11).

### 3.2 Das Datenmodell muss von Einzel- auf Mengen-Import umgestellt werden

`1 Upload = 1 Dokument` trägt nicht. Ordner und PST erzeugen je Vorgang viele Dokumente. Es braucht ein **Batch**-Objekt (Eltern) über N **Element**-Jobs (Kinder) mit eigenem Status. Dies ist der gemeinsame Kern (Abschnitt 5) und Voraussetzung für beide Features. Konsequenz: Teil-Erfolg wird zum Normalfall — „alles oder nichts" ist hier fachlich falsch.

### 3.3 Was ist bei PST eine „Dokumenteneinheit"?

Eine PST enthält Ordnerstruktur, E-Mails, Kalendereinträge, Kontakte, Anhänge. Bevor irgendetwas gebaut wird, muss definiert sein, was zur kanonischen Markdown-Quelle wird (Abschnitt 7.1). Ohne diese Festlegung ist „PST importieren" nicht abnahmefähig, weil unklar bleibt, wie viele Dokumente herauskommen.

### 3.4 Dedup-Verhalten bei Massen-Import

Der bestehende `UniqueConstraint(workspace_id, content_hash)` wirft heute bei identischem Inhalt einen Fehler. Bei Ordner/PST sind Duplikate der Normalfall (gleiche Datei in Unterordnern; dieselbe Mail in mehreren PST-Ordnern; Mail + Weiterleitung). „Duplikat" darf den Batch **nicht** als Fehler abbrechen, sondern muss als eigener Element-Status `skipped_duplicate` geführt werden (Abschnitt 5.3).

---

## 4. Userflow (Importcenter, beide Features)

1. Nutzer öffnet Importcenter.
2. Auswahl der Importart: `Einzeldatei` (bestehend) | `Ordner` (neu) | `Outlook-PST` (neu).
3. Quelle wählen:
   - Ordner: Ordner-Dialog des Browsers (`webkitdirectory`), Auswahl per Mausklick. Angezeigt wird der Ordnername. Das Frontend filtert vor dem Upload auf unterstützte Typen und Ausschlussliste.
   - PST: Datei-Dialog, Filter `*.pst`.
4. **Vorab-Prüfung (Pflicht, vor dem eigentlichen Import):** System zeigt eine Übersicht: Anzahl gefundener Elemente, davon unterstützt / nicht unterstützt / leer, geschätzte Gesamtgröße, erkannte Duplikate. Kein Import startet ohne diese bestätigte Übersicht.
5. Nutzer bestätigt oder grenzt ein (z. B. Dateityp-Filter).
6. Batch-Import startet. Fortschritt live: `x von N verarbeitet`, Zähler je Status.
7. Abschluss: Ergebnisbericht (Abschnitt 5.4), exportierbar/kopierbar.

---

## 5. Gemeinsamer Baustein: Batch-Import (Voraussetzung für F1 und F2)

### 5.1 Datenmodell (neu)

- `import_batch`: `id`, `workspace_id`, `source_type` (`folder` | `pst`), `source_label` (Ordnername bzw. PST-Dateiname), `created_by`, `created_at`, `status`, `total_count`, Zählerfelder je Element-Status, `correlation_id`.
- `import_batch_item`: `id`, `batch_id` (FK), `relative_path` (Ordner) bzw. `mailbox_path` + `message_id` (PST), `filename`, `mime_type`, `status`, `error_code`, `document_id` (FK, nullable), `content_hash` (nullable).
- Beziehung zu `documents`: erfolgreiche Items verweisen auf das erzeugte Dokument.

### 5.2 Batch-Status (Eltern)

`pending` → `running` → `completed` | `completed_with_errors` | `failed` | `cancelled`.

- `completed`: alle Items `succeeded` oder `skipped_duplicate`.
- `completed_with_errors`: mindestens ein Item `failed`, mindestens eines `succeeded`.
- `failed`: kein Item erfolgreich **oder** Quelle nicht lesbar/zerlegbar.
- `cancelled`: Nutzerabbruch; bereits importierte Items bleiben bestehen (kein Rollback der Erfolge).

### 5.3 Element-Status (Kind)

`pending` → `running` → `succeeded` | `failed` | `skipped_unsupported` | `skipped_empty` | `skipped_duplicate` | `skipped_too_large`.

`skipped_*` sind **kein** Batch-Abbruchgrund. Nur Infrastrukturfehler (DB nicht erreichbar, Quelle nicht lesbar) brechen den Batch ab.

### 5.4 Ergebnisbericht (Pflicht-Deliverable je Batch)

Tabellarisch, je Element: Pfad/Quelle, Dateiname, Status, Fehlercode/-text, verknüpfte Dokument-ID. Plus Aggregat: gesamt, erfolgreich, übersprungen (je Grund), fehlgeschlagen. Der Bericht ist die Grundlage der Abnahme (Abschnitt 9) und muss persistiert sein, nicht nur flüchtig im UI.

### 5.5 Verarbeitung

- Items werden **einzeln** durch die bestehende Pipeline (`parse → ocr → normalize → hash → persist`) geschickt. Die Pipeline wird **nicht** dupliziert.
- Sequentiell oder begrenzt parallel (Default: sequentiell, Konfig später). OCR-lastige Elemente nicht unbegrenzt parallelisieren.
- Idempotenz: erneuter Import desselben Ordners/derselben PST erzeugt keine Doubletten (greift über `content_hash` → `skipped_duplicate`).
- Fortschritt wird pro Item fortgeschrieben (kein „Big-Bang"-Update am Ende), damit der Live-Zähler real ist.

---

## 6. Feature 1 — Ordner-Import

### 6.1 Funktionale Anforderungen

- F1-01: Nutzer wählt per Mausklick einen Ordner (`<input type="file" webkitdirectory>`). Der Browser ermittelt alle enthaltenen Dateien rekursiv.
- F1-02: Frontend filtert **vor** dem Upload auf Dateitypen mit registriertem Parser und auf die Ausschlussliste (F1-09), damit nicht der ganze Ordner unnötig hochgeladen wird. Übrige Typen werden im Vorab-Bericht als `skipped_unsupported` ausgewiesen, nicht hochgeladen.
- F1-03: Nur Dateitypen mit registriertem Parser werden importiert (heute: txt, md, docx, doc, pdf).
- F1-04: Vorab-Prüfung (Abschnitt 4) zeigt je Typ Anzahl und Gesamtgröße sowie das resultierende **Upload-Volumen**; Nutzer kann Typen abwählen und sieht, was übertragen wird, bevor er startet.
- F1-05: Pro Datei wird der relative Pfad (`webkitRelativePath`) als Metadatum am Dokument gespeichert (Herkunftsnachvollziehbarkeit; Telekom-Anforderung Wissenssicherung).
- F1-06: Leere Dateien → `skipped_empty`. Dateien über Einzel-Limit (50 MB) → `skipped_too_large` (bereits im Frontend erkannt, nicht hochgeladen).
- F1-07: Inhaltsgleiche Dateien (gegen Workspace und innerhalb des Batches) → `skipped_duplicate`.
- F1-08: Batch ist abbrechbar; laufendes Element wird sauber beendet, danach Stopp. Bereits hochgeladene, noch nicht verarbeitete Elemente werden verworfen.
- F1-09: Ausschlussliste für Systemdateien (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `.git/`, …), Standard aktiv, konfigurierbar.

#### 6.1.1 Upload-Eingang (neu, variante-A-spezifisch)

Der bestehende Endpunkt `POST /documents/import` nimmt genau eine Datei und ist für Variante A unzureichend. Vorschlag:

- Neuer Eingang, der einen **Batch eröffnet** und die Dateien des Ordners aufnimmt. Zwei Umsetzungsmuster (Detailentscheidung Technik, nicht fachlich blockierend):
  1. `POST /imports/folder` eröffnet den Batch (liefert `batch_id`); Frontend lädt die Dateien einzeln/chunked gegen `POST /imports/folder/{batch_id}/items` hoch und schließt mit `POST /imports/folder/{batch_id}/start` ab.
  2. Alternativ ein Multipart-Sammelupload — nur für kleine Ordner tragfähig, bei großen Mengen riskant (Timeout, Speicher). Muster 1 wird empfohlen.
- Jede Datei trägt ihren `webkitRelativePath` als Feld mit, da der Server keinen Pfad kennt.

### 6.2 Edge Cases (zu spezifizieren, nicht offenlassen)

- Dateinamen mit Umlauten/Sonderzeichen/Unicode-Normalisierung (NFC/NFD) — relevant für Pfad-Metadaten und Dedup; relativer Pfad normalisiert speichern.
- Gleiche Datei in mehreren Unterordnern → einmal importiert, übrige `skipped_duplicate` (alle Pfade dennoch protokolliert).
- Sehr großer Ordner: zentrales Risiko ist das **Upload-Volumen/-Dauer** und der Browser-Speicher beim Einlesen der Dateiliste. Vorab-Prüfung muss Anzahl und Upload-Volumen nennen, bevor gestartet wird; harte Obergrenze greift (F1 → E2).
- Upload-Abbruch / Verbindungsverlust mitten im Batch: bereits verarbeitete Elemente bleiben gültig; Batch geht in `cancelled`/`completed_with_errors`; Wiederholung greift über Dedup (`skipped_duplicate`).
- Datei, die der Browser nicht lesen kann (gesperrt/Berechtigung): Element → `failed` mit `read_denied`, kein Batch-Abbruch.
- Passwortgeschützte PDF/DOCX im Ordner: `failed` mit definiertem Code (kein stiller Skip).
- Leere Auswahl / Ordner ohne unterstützte Dateien: klare Meldung, kein Batch-Start.

### 6.3 Validierung / Grenzen

- Harte Obergrenzen: Anzahl Dateien je Batch **und** Upload-Gesamtvolumen. Default-Vorschlag: 5.000 Dateien / 2 GB Upload. Zu bestätigen (E2).
- Pro-Datei-Limit bleibt 50 MB (bestehend), bis explizit angehoben.
- Überschreitung der Obergrenze: Block vor Upload-Start mit Hinweis auf Aufteilung, kein Teil-Upload „bis es bricht".

---

## 7. Feature 2 — Outlook-PST-Import

### 7.1 Dokumenteneinheit (Kernfestlegung, Entscheidung E3)

Vorschlag (zu bestätigen):

- **Jede E-Mail → ein Markdown-Dokument.** Kopf (Von, An, CC, Datum, Betreff, Message-ID, Quell-Ordnerpfad) als strukturierter Metadatenblock; Body als Markdown.
- **Anhänge:** Standard = jeder Anhang mit unterstütztem Typ wird als **eigenes** Dokument importiert und mit der Mail verknüpft (Metadatum `parent_message_id`). Alternative: Anhänge ignorieren. Zu entscheiden (E3).
- **Kalender/Kontakte/Aufgaben:** in V1 **out of scope** (Vorschlag), sonst eigene Modellierung nötig.

Ohne diese Festlegung ist die erzeugte Dokumentanzahl und damit die Abnahme nicht definiert.

### 7.2 Technische Voraussetzung — neue Parser

- PST ist heute **nicht** lesbar. Es braucht eine PST-Lesekomponente (z. B. `libpff`/`pypff` bzw. `readpst`/libpst) — Lizenz- und Betriebsfreigabe bei der Telekom **vor** Umsetzung klären (E4).
- Zusätzlich ein Parser für die extrahierten Einzelnachrichten (`.eml`/MIME, ggf. `.msg`) inkl. Mapping in den Metadatenblock aus 7.1.
- Beide Parser reihen sich in die bestehende `ParserSelector`-Logik ein; die Pipeline bleibt unverändert.

### 7.3 Funktionale Anforderungen

- F2-01: Nutzer wählt eine `.pst`-Datei (Filter `*.pst`).
- F2-02: System liest die Mailbox-Struktur und zeigt in der Vorab-Prüfung: Anzahl Mails gesamt, je Ordner, Anzahl Anhänge, geschätzte resultierende Dokumentanzahl, erkannte Duplikate.
- F2-03: Pro Mail ein Dokument gemäß 7.1; Quell-Ordnerpfad innerhalb der PST als Metadatum.
- F2-04: Anhänge gemäß Entscheidung E3.
- F2-05: Dedup über `content_hash`; identische Mail in mehreren Ordnern → einmal, Rest `skipped_duplicate`.
- F2-06: Fortschritt und Ergebnisbericht über das Batch-Modell (Abschnitt 5).

### 7.4 Edge Cases

- **Große PST (mehrere GB):** sprengt das aktuelle In-Memory-Modell (`source_bytes` lädt die ganze Datei in den Speicher). PST muss auf Temp-Datei gestreamt und elementweise extrahiert werden — **nicht** als ein 50-MB-Upload behandelbar. Das 50-MB-Limit gilt für die PST als Ganzes **nicht**, sondern pro extrahiertem Element.
- **ANSI- vs. Unicode-PST** (alt/neu): Lesekomponente muss beide können.
- **Passwortgeschützte/verschlüsselte PST:** definierter Fehler, kein Crash. Passworteingabe = Entscheidung E5.
- **Korrupte/teildefekte PST:** lesbare Mails importieren, defekte als `failed` protokollieren, Batch nicht abbrechen.
- **Eingebettete Mails** (Mail als Anhang einer Mail): Verhalten festlegen (rekursiv extrahieren vs. als Anhang behandeln).
- **HTML- vs. Plaintext-Mails:** HTML → Markdown normalisieren; reine Plaintext direkt.
- **Inline-Bilder / `cid:`-Referenzen:** Verhalten festlegen (verwerfen vs. als Anhang).
- **Zeitzonen/Datumsformate** im Kopf: normalisiert nach ISO 8601.
- **Dubletten Mail vs. Weiterleitung/Antwort:** unterschiedlicher Inhalt → kein Dedup; nur byte-/inhaltsgleiche werden übersprungen.

### 7.5 Validierung / Grenzen

- Obergrenze Mails je PST-Batch festlegen (Vorschlag: 50.000, zu bestätigen E2).
- Temp-Speicherbedarf für Extraktion einplanen und im Health-Check abdecken.

---

## 8. Nicht-funktionale Anforderungen

- **Nachvollziehbarkeit (Telekom-Wissenssicherung):** Jede Herkunft (Ordnerpfad bzw. PST-Ordner + Message-ID) bleibt am Dokument als Metadatum erhalten.
- **Robustheit:** Ein fehlerhaftes Element darf den Batch nie abbrechen. Nur Infrastrukturfehler tun das.
- **Wiederanlauf:** Bei Absturz während des Batches muss der Vorgang fortsetzbar oder sauber wiederholbar sein, ohne Doubletten (Idempotenz über `content_hash`). Anschluss an bestehende `import_recovery`-Mechanik prüfen.
- **Beobachtbarkeit:** Batch- und Element-Ereignisse über das bestehende `log_import_event`/Korrelations-ID-Schema.
- **Performance-Transparenz:** Vorab-Prüfung muss Größe/Anzahl realistisch melden, damit der Nutzer vor langen Läufen entscheidet.
- **Datenschutz:** PST/E-Mail enthalten personenbezogene Daten. Verarbeitungszweck, Speicherort der Temp-Extrakte und deren Löschung nach Verarbeitung sind festzulegen (Telekom-DSGVO-Kontext).

---

## 9. Abnahmekriterien (Maßstab: fehlerfreier Live-Lauf)

Ordner-Import:

- AK-1: Realer Ordner mit gemischten Typen (txt, md, docx, doc, pdf, plus mind. ein nicht unterstützter Typ, eine leere Datei, ein Duplikat) wird live importiert.
- AK-2: Ergebnisbericht weist jede Datei korrekt zu (`succeeded` / `skipped_unsupported` / `skipped_empty` / `skipped_duplicate`); Zähler stimmen mit dem Ordnerinhalt überein.
- AK-3: Jedes erfolgreiche Dokument trägt den korrekten `relative_path` als Metadatum.
- AK-4: Erneuter Import desselben Ordners erzeugt 0 neue Dokumente (alle `skipped_duplicate`).
- AK-5: Abbruch mitten im Lauf hinterlässt konsistenten Zustand (importierte Dokumente gültig, keine halben Dokumente).

PST-Import:

- AK-6: Reale PST (Unicode, mehrere Ordner, mit Anhängen) wird live importiert; resultierende Dokumentanzahl entspricht der in der Vorab-Prüfung genannten Zahl.
- AK-7: E-Mail-Kopf (Von/An/Datum/Betreff/Quell-Ordner/Message-ID) ist je Dokument vollständig und korrekt.
- AK-8: Anhänge gemäß Entscheidung E3 verknüpft (`parent_message_id`).
- AK-9: Korrupte/teildefekte PST: lesbare Mails importiert, defekte als `failed` protokolliert, kein Abbruch.
- AK-10: Dieselbe Mail in zwei PST-Ordnern → ein Dokument, Rest `skipped_duplicate`.

Querschnitt:

- AK-11: Kein Einzelfehler bricht den Batch ab.
- AK-12: Batch- und Ergebnisbericht sind persistiert und nach Sitzungsende abrufbar.

---

## 10. Offene Entscheidungen (blockierend — bitte vor Umsetzung klären)

- **E1 — Deployment-Variante Ordner-Import:** ✅ **entschieden — Variante A (`webkitdirectory`).** Folgen eingearbeitet (Abschnitte 3.1, 6.1, 6.1.1). Pfad-/Desktop-Variante verschoben auf Phase 2.
- **E2 — Mengen-Obergrenzen:** Max. Dateien/Volumen je Ordner-Batch; max. Mails je PST-Batch.
- **E3 — PST-Dokumenteneinheit & Anhänge:** Mail = ein Dokument bestätigt? Anhänge als eigene Dokumente, oder ignorieren?
- **E4 — PST-Lesekomponente:** Lizenz-/Betriebsfreigabe der gewählten Bibliothek im Telekom-Kontext.
- **E5 — Passwortgeschützte PST:** Passworteingabe anbieten oder generell ablehnen?
- **E6 — Datenschutz:** Verarbeitungszweck und Löschkonzept für Temp-Extrakte aus PST.

Diese Punkte werden bewusst nicht mit Annahmen gefüllt; sie ändern das Design substanziell.

---

## 11. Out of Scope (V1 dieser Erweiterung)

- Ordner-Überwachung / automatische Re-Synchronisation bei Änderungen (mit Variante A technisch nicht möglich — kein persistenter Pfad).
- Pfad-basierter Ordner-Import mit nativem OS-Dialog (vormals Variante B) — verschoben auf die geplante Phase-2-Desktop-Hülle.
- Kalender-, Kontakt- und Aufgabeneinträge aus PST.
- Weitere Mailbox-Formate (OST, MBOX, Exchange-Online-Direktanbindung).
- Server-seitiger Zugriff auf beliebige Netzlaufwerkspfade ohne Nutzerauswahl.
- Anhebung des Pro-Datei-Limits über 50 MB.
