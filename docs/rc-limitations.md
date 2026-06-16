# RC Limitation Register — Ruflo 1.0 Release Candidate

Stand: 2026-06-16
Maschinenlesbare Quelle: `reports/current/rc_limitation_register.json`

---

## Geltungsbereich

Dieses Dokument listet alle bekannten Limitationen, die bei Erteilung eines CONDITIONAL_RC (Release Candidate) dokumentiert und kommuniziert sein müssen. Keine der aufgeführten Limitationen blockiert RC direkt. RCL-01 blockiert GA.

---

## RCL-01 — GP-07 Export: kein PDF-Export in 1.0

**Quelle:** gold_path_missing_step_analysis.json, Gold Path Schritt GP-07
**Risiko:** Mittel
**Blockiert RC:** Nein
**Blockiert GA:** Ja

Export Center liefert JSON und Markdown. PDF-Export ist auf Version 1.1 verschoben. GP-07 erreicht CONDITIONAL_PASS, nicht PASS. Nutzer mit strikter PDF-Anforderung (Drucken, formale Ablage) sind eingeschränkt. JSON-Export kompensiert den Datenzugriff vollständig.

**Workaround:** JSON-Export für Datenabzug, Markdown für Dokumentation und Archivierung.
**PO-Entscheidung erforderlich:** Ist JSON/MD-Export ausreichend für CONDITIONAL_RC-Freigabe?
**Ziel-Fix:** Version 1.1 oder PO-Entscheidung: GP-07 auf JSON/MD-Basis als GA-ausreichend werten.

---

## RCL-02 — Dashboard W06: Drift-Widget nicht implementiert

**Quelle:** product_release_gate.json, Feature-Gate G01
**Risiko:** Niedrig
**Blockiert RC:** Nein | **Blockiert GA:** Nein

Dashboard-Kernfunktionen W01–W05 PASS. W06 Drift-Widget benötigt GET /api/v1/dashboard/drift — Endpoint fehlt. Dashboard zeigt Platzhalter. Drift-Status ist über die /drift-Seite erreichbar.

**Workaround:** /drift-Seite für Drift-Status nutzen.
**Ziel-Fix:** Version 1.0 Sprint oder 1.1.

---

## RCL-03 — Tags-API unvollständig (Anlegen/Entfernen fehlt)

**Quelle:** product_release_gate.json, P1-GAP-01/02
**Risiko:** Mittel
**Blockiert RC:** Nein | **Blockiert GA:** Nein

POST /api/v1/documents/:id/tags und DELETE fehlen. Vorhandene Tags werden korrekt angezeigt. Nachträgliche Tag-Zuweisung oder -Entfernung über die UI ist nicht möglich.

**Workaround:** Tags vor Import in Dokumenten-Metadaten hinterlegen.
**Ziel-Fix:** Version 1.0 Sprint oder 1.1.

---

## RCL-04 — GP-05 Analyse starten: Workflow-Schritte 5+7 ungeklärt (PO-Risiko)

**Quelle:** gold_path_missing_step_analysis.json, Sekundärrisiko GP-05
**Risiko:** Hoch (wenn PO-Entscheidung ausbleibt)
**Blockiert RC:** Nein (bei PO-Entscheidung) | **Blockiert GA:** Nein

Analyse-Workflow-Schritte 5 (Vorschläge anzeigen) und 7 (Übernahme in Dokumentenstruktur) sind inhaltlich nicht spezifiziert. Wenn bis Sprint-Ende ungeklärt: GP-05 CONDITIONAL_PASS statt PASS, Gold Path fällt auf ≤6/8 — unter RC-Minimum 7/8.

**Workaround:** PO-Entscheidung vor Sprint-Start erzwingen.
**Ziel-Fix:** PO muss Schritte 5+7 vor Sprint-Start spezifizieren.
**PO-Entscheidung erforderlich:** Welche Aktionen sind für Analyse-Schritte 5 und 7 vorgesehen?

---

## RCL-05 — OCR für gescannte PDFs nicht in 1.0

**Quelle:** known_limitations.json — KL-DEF-001
**Risiko:** Niedrig
**Blockiert RC:** Nein | **Blockiert GA:** Nein

Gescannte PDFs ohne extrahierbaren Text bleiben im Status OCR_REQUIRED und können nicht verarbeitet werden. Primäre Zielgruppe (text-basierte Dokumente) nicht betroffen.

**Workaround:** Nur text-basierte PDFs, DOCX und Plaintext importieren.
**Ziel-Fix:** Version 1.1 oder dediziertes Feature-Paket.

---

## RCL-06 — API-Routing-Inkonsistenz: /documents/* statt /api/v1/documents/*

**Quelle:** known_limitations.json — KL-NB-001
**Risiko:** Niedrig
**Blockiert RC:** Nein | **Blockiert GA:** Nein

documents_router ist unter /documents/* gemountet. Externe API-Konsumenten müssen /documents/ verwenden, nicht /api/v1/documents/. Verhalten ist in docs/api.md dokumentiert.

**Workaround:** API-Vertrag vor Clientbindung prüfen.
**Ziel-Fix:** Version 1.1 — Routing konsolidieren.

---

## Zusammenfassung

| ID | Titel | Blockiert RC | Blockiert GA | PO-Entscheidung |
|----|-------|-------------|--------------|-----------------|
| RCL-01 | GP-07 Export: kein PDF | Nein | **Ja** | **Ja** |
| RCL-02 | Dashboard W06 fehlt | Nein | Nein | Nein |
| RCL-03 | Tags-API unvollständig | Nein | Nein | Nein |
| RCL-04 | GP-05 Workflow ungeklärt | Nein (wenn PO entscheidet) | Nein | **Ja** |
| RCL-05 | OCR fehlt | Nein | Nein | Nein |
| RCL-06 | API-Routing-Inkonsistenz | Nein | Nein | Nein |

Aktueller RC-Status: **BLOCKED** (Score 53 < 80, Gold Path 4/8 < 7/8).
CONDITIONAL_RC ist erst nach Sprint-Abschluss (T09–T33) evaluierbar.
