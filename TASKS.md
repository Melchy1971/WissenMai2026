# Tasks

## In Progress

*(nichts aktiv)*

## Todo

### Produktlücken-Sprint für 1.0 (nächster Schritt)

Sprint-Details in `tasks/product_gap_tasks.md` (T01–T39) und `docs/product_gap_sprint.md`.

**Kritische Blocker — zuerst:**
- [ ] T09–T10 — Topics ORM-Models (Category, Tag, Topic, DocumentTag)
- [ ] T11–T15 — Topics API (GET/POST /api/v1/topics, GET /api/v1/topics/:id)
- [ ] T17 — URL-Bug in api/topics.js beheben (/api/v1/-Präfix fehlt)
- [ ] T18–T19 — KI-Zusammenfassung für Topics (Ollama-Integration)
- [ ] T25–T27 — AnalysisPage.jsx implementieren (AGAP-07) + ApproveButton
- [ ] T05–T07 — Cancel-Endpunkt für Analyse-Jobs (AGAP-02)
- [ ] T28–T33 — Export Center MVP (POST /api/v1/export, JSON + Markdown, ExportButton)
- [ ] T34–T37 — Dashboard W06 Drift Widget + GET /api/v1/dashboard/drift
- [ ] DC-F01 — UUIDs aus DocumentMetaCard entfernen (< 1h)

Nach Sprint: `product_maturity_v2.json` + `version_1_0_candidate_gate.json` neu evaluieren.

### Offen nach Sprint (für Score 85 nötig)

- [ ] Lazy Loading in Dokumentenvorschau (PV-F01)
- [ ] KWIC-Highlighting in Suche (SR-F01)
- [ ] Deutsches FTS-Stemming in PostgreSQL (SR-F02)
- [ ] Tags vollständig: Filter + Zuweisung im UI
- [ ] Retry-Button für Dokumente mit importStatus='error' (DC-F04)

### PO-Diskussion ausstehend

- [ ] Schwellwert 85 für 1.0 vs. 80 für RC / 85 für GA klären (nach Sprint erwartet: ~78–82)
- [ ] Schritt 5 (Vorschläge) und Schritt 7 (Übernahme) im Analyse-Workflow inhaltlich klären

## 1.1 / nach Scope Freeze (NICHT Teil des 1.0-Sprints)

> Außerhalb des 1.0 Scope Freeze. Erst nach 1.0-Gate angehen. Stories/Konzept in `OUTPUTS/Importcenter-Erweiterung/`.

### Importcenter-Erweiterung — Ordner-Import (Feature 1, Variante A entschieden)

- [ ] ENB-1 — Datenmodell `import_batch` / `import_batch_item` (Migration)
- [ ] ENB-2 — Batch-Upload-Eingang (eröffnen → Items → start)
- [ ] ENB-3 — Fan-out über bestehende Pipeline (Pro-Element-Status)
- [ ] ENB-4 — Fortschritt/Status-Abfrage (Live-Zähler)
- [ ] ENB-5 — Ergebnisbericht (persistiert)
- [ ] F1-S1..S9 — Ordnerauswahl (webkitdirectory), Vorab-Prüfung, relative_path, Dedup, Skip-Klassen, Ausschlussliste, Obergrenzen (hängt an E2), Abbruch, Fehlerbehandlung

### Importcenter-Erweiterung — Outlook-PST-Import (Feature 2, offen)

- [ ] Offene Entscheidungen klären: E2 (Obergrenzen), E3 (PST-Dokumenteneinheit/Anhänge), E4 (PST-Bibliothek Lizenz/Freigabe), E5 (passwortgeschützte PST), E6 (Datenschutz/Löschkonzept)
- [ ] F2-Stories nach Entscheidung E3 ableiten (nutzt ENB-1..5)

## Someday / Backlog

- PDF-Export (1.1)
- PATCH /documents/:id für Metadaten
- Kategorien-Hierarchie (P3)
- Mobile-optimiertes UI
- i18n

## Done

- [x] #48 document_center_product_ready.json
- [x] #49 document_preview_ready.json
- [x] #50 topic_center_product_ready.json
- [x] #51 search_experience_ready.json
- [x] #52 export_center_product_ready.json
- [x] #53 analysis_ux_ready.json
- [x] #54 product_gold_path.json
- [x] #55 docs/version_1_0_scope_freeze.md
- [x] #56 product_maturity_v2.json (Score: 52/85)
- [x] #57 version_1_0_candidate_gate.json (BLOCKED)
