# Cleanup Dry Run Architektur (M5)

## Ziel
Niemals direkt löschen. Jeder Löschvorgang durchläuft einen mehrstufigen, dokumentierten Prozess.

## Modi
1. **Analyse:**
   - Systematische Erkennung von Löschkandidaten (Duplikate, verwaiste Chunks/Versionen, ungültige Metadaten, historische Artefakte)
   - Erzeugt einen Analyse-Report
2. **Vorschlag:**
   - Generiert einen konkreten Löschvorschlag (JSON), inkl. Kandidatenliste und Begründung
3. **Dry Run:**
   - Simuliert die Löschung, berechnet Auswirkungen (z.B. wie viele Chunks/Versionen betroffen wären)
   - Kein Datenverlust, alle Aktionen reversibel
   - Dry-Run-Report dokumentiert alle Effekte
4. **Freigabe:**
   - Review und explizite Freigabe durch Gate-Board oder verantwortliche Person
   - Dokumentation der Entscheidung (Audit-Trail)
5. **Ausführung:**
   - Erst nach Freigabe erfolgt die tatsächliche Löschung
   - Alle gelöschten Objekte werden protokolliert

## Bewertete Objekttypen
- Duplicate Dokumente
- Verwaiste Chunks
- Verwaiste Versionen
- Ungültige Metadaten
- Historische Artefakte (z.B. alte Uploads, Dead-Letter-Jobs)

## Reports & Audit
- Jeder Schritt erzeugt einen Report (Analyse, Vorschlag, Dry Run, Freigabe, Ausführung)
- Audit-Trail für jede Löschaktion
- Kein produktiver Cleanup ohne dokumentierte Dry-Run-Phase und explizite Freigabe

## Gate-Kriterien
- Cleanup darf nur ausgeführt werden, wenn `blocked_count = 0` im Dry-Run-Report
- Jede Ausnahme muss dokumentiert und genehmigt werden
