# Datenanalyse-Workflow

**Datum:** 2026-06-12
**Ziel:** Geführter Workflow für neue Dokumente — von Import bis Freigabe in die Wissensbasis
**Hintergrund:** Data Quality und Drift arbeiten im Hintergrund. Der Anwender sieht fachliche Ergebnisse, keine technischen Prozesse.

---

## Konzept

Der Datenanalyse-Bereich ist der geführte Pfad für neue Wissenseinheiten. Ein Dokument wird nicht einfach "hochgeladen" — es wird verarbeitet, analysiert und mit dem bestehenden Wissensbestand verglichen, bevor es für die Suche freigegeben wird. Der Anwender entscheidet am Ende, ob das Dokument übernommen wird.

---

## Workflow-Übersicht

```
[1] Neue Dokumente
       │  Datei(en) auswählen oder per Drag & Drop
       ▼
[2] KI-Analyse
       │  Automatisch: Texterkennung, Strukturierung, Tag-Vorschlag
       ▼
[3] Vergleich mit Bestand
       │  Ähnliche Dokumente anzeigen — Duplikatprüfung
       ▼
[4] Zusammenfassung
       │  KI erstellt Dokumentzusammenfassung zur Prüfung
       ▼
[5] Vorschlag
       │  System schlägt Kategorie, Tags, Thema vor
       ▼
[6] Freigabe
       │  Anwender prüft und bestätigt oder korrigiert
       ▼
[7] Übernahme
          Dokument ist aktiv und durchsuchbar
```

---

## Schritt 1: Neue Dokumente

- Unterstützte Formate: TXT, MD, DOCX, DOC, PDF (mit extrahierbarem Text)
- Drag & Drop oder Dateiauswahl
- Mehrere Dateien gleichzeitig möglich (Queue)
- Direktes Feedback: Format erkannt / nicht erkannt
- Bei PDF ohne Text: "Dieses PDF enthält keinen lesbaren Text. Bitte als durchsuchbares PDF exportieren."

---

## Schritt 2: KI-Analyse

- Automatisch, ohne Nutzerinteraktion
- Anzeige: Fortschrittsanzeige ("Dokument wird analysiert…")
- Hintergrund-Prozesse (für den Anwender nicht sichtbar):
  - Textextraktion
  - Markdown-Normalisierung
  - Chunking
  - Tag-Extraktion
- Fehler werden verständlich gemeldet: "Dokument konnte nicht gelesen werden. Bitte Format prüfen."

---

## Schritt 3: Vergleich mit Bestand

- Zeigt ähnliche Dokumente im Bestand (Ähnlichkeit nach Inhalt, nicht nach Hash)
- Anzeige: "Ähnliche Dokumente gefunden:"
  - [Dokumenttitel] — [Ähnlichkeitshinweis: "Sehr ähnlich" / "Teilweise ähnlich"]
- Anwender entscheidet: Neues Dokument trotzdem hinzufügen oder abbrechen
- Bei exaktem Duplikat: "Dieses Dokument ist bereits in der Wissensbasis. Kein Duplikat erlaubt."

---

## Schritt 4: Zusammenfassung

- KI erstellt eine 3–5-Satz-Zusammenfassung des Dokuments
- Anwender kann Zusammenfassung lesen und bestätigen oder überspringen
- Zusammenfassung wird im Dokumentdetail gespeichert und im Themenzentrum verwendet

---

## Schritt 5: Vorschlag

System schlägt vor:

| Feld | Vorschlag | Editierbar |
|------|-----------|-----------|
| Titel | Aus Dateiname oder Dokumentkopf | ja |
| Kategorie | KI-Vorschlag, als "Vorgeschlagen" markiert | ja |
| Tags | KI-Vorschlag, max. 5 Tags | ja — hinzufügen / entfernen |
| Thema | Passendes Thema (falls vorhanden) | ja |

Alle Vorschläge sind bearbeitbar. KI-generierte Felder sind visuell markiert (z.B. Stern-Icon).

---

## Schritt 6: Freigabe

- Zusammenfassung aller Angaben
- Bestätigungsbutton: "Dokument in Wissensbasis aufnehmen"
- Alternativ: "Abbrechen" — Dokument wird verworfen, kein Eintrag im System

---

## Schritt 7: Übernahme

- Dokument erhält Status "aktiv"
- Erscheint in der Dokumentliste und ist über die Suche auffindbar
- Erfolgsanzeige: "Dokument erfolgreich aufgenommen. [Dokument ansehen →]"

---

## Data Quality und Drift im Hintergrund

Data Quality und Drift Detection laufen als Systemdienste. Der Anwender sieht:

- Im Dashboard: "Qualitätshinweise" — verständlich formuliert, mit Handlungsempfehlung
- Kein technischer Score, kein Report-Link
- Beispiel: "3 Dokumente haben möglicherweise veraltete Inhalte. [Jetzt prüfen →]"

Was der Anwender **nicht** sieht:

- Gate-Status (M5a, M5b, M5c)
- DQ Score als Zahl
- Drift-Detektoren und ihre Ergebnisse
- Cleanup-Operationen
- Report-Dateien

---

## Nicht enthalten

- Admin-Aktionen (Reindex, Repair, Cleanup)
- Governance-Workflows
- Batch-Verarbeitung ohne Nutzerinteraktion
- Embedding-Konfiguration
