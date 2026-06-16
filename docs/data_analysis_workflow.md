# Datenanalyse-Workflow

**Datum:** 2026-06-16 (aktualisiert nach PRI-2 Abschluss, Tasks #74–#82)
**Ziel:** Geführter Workflow für neue Dokumente — von Import bis Freigabe in die Wissensbasis
**Hintergrund:** Data Quality und Drift arbeiten im Hintergrund. Der Anwender sieht fachliche Ergebnisse, keine technischen Prozesse.
**Implementierungsstatus:** Vollständig implementiert. Alle 7 Schritte produktionsreif. Gold-Path GP-A01–GP-A11: 11/11 PASS.

---

## Konzept

Der Datenanalyse-Bereich ist der geführte Pfad für neue Wissenseinheiten. Ein Dokument wird nicht einfach "hochgeladen" — es wird verarbeitet, analysiert und mit dem bestehenden Wissensbestand verglichen, bevor es für die Suche freigegeben wird. Der Anwender entscheidet am Ende, ob das Dokument übernommen wird.

---

## Workflow-Übersicht

```
[1] Dokument auswählen (AnalysisPage → NewAnalysisJobDialog)
       │  Multi-Select aus Dokumentenzentrum (status='chunked')
       ▼
[2] Analyse-Job anlegen
       │  POST /api/v1/analysis/jobs → status=queued
       ▼
[3] KI-Analyse (asynchron)
       │  Polling über AnalysisJobList bis status=completed
       ▼
[4] Ergebnis anzeigen (AnalysisResultPanel)
       │  summary, key_points, suggestedTags, suggestedTopics, confidence
       ▼
[5] Zur Prüfung einreichen
       │  POST /results/:id/review → status=review
       ▼
[6] Freigabe (Workspace-Admin)
       │  POST /results/:id/approve (confirm=True Pflicht) → status=approved
       │  Alternativ: POST /results/:id/reject → status=rejected
       ▼
[7] In Wissensbasis importieren
          POST /results/:id/import → Tags + Topics in KB
          btn-import nur sichtbar wenn status=approved (Import-Guard)
          Idempotent: zweiter Import erzeugt keine Duplikate
```

Implementierte Komponenten: `AnalysisPage.jsx`, `AnalysisJobList.jsx`, `AnalysisJobDetail.jsx`, `AnalysisResultPanel.jsx`, `NewAnalysisJobDialog.jsx` (5-Step-Wizard), `useAnalysis.js`, `api/analysis.js`.

---

## Schritt 1: Dokument auswählen

- Einstieg über `/analysis` → Button "Neue Analyse"
- `NewAnalysisJobDialog` öffnet einen 5-Step-Wizard
- Schritt 1: Multi-Select aus Dokumentliste (nur `lifecycle_status='active'`, `status='chunked'`)
- Schritt 2: Analyse-Typ wählen (`summary`, `compare`, `full`)
- Schritte 3–5: Optionaler Fokus-Prompt, Bestätigung, Job-Start

---

## Schritt 2: Analyse-Job anlegen

- `POST /api/v1/analysis/jobs` mit `source_document_ids` + `analysis_type`
- Response: `{ id, status: 'queued', workspace_id, created_at }`
- Backend: `AnalysisService.create_job()` → ORM-Eintrag in `analysis_jobs`

---

## Schritt 3: KI-Analyse (asynchron)

- `AnalysisJobList` pollt `GET /api/v1/analysis/jobs` in Intervallen (250 ms)
- `AnalysisStatusBadge` zeigt aktuellen Status: `queued → pending → running → completed`
- Fehlerfall: `status='failed'` → `job-error-block` mit `error_code` und `error_message`
- Abbruch: `btn-cancel-job` für queued/pending/running — `POST /jobs/:id/cancel`
- Wiederholung: `btn-retry-job` für failed/cancelled — `POST /jobs/:id/retry`
- KI-Provider: `OllamaLlmProvider` (Produktion), `DeterministicAnalysisStubEngine` (Tests)

---

## Schritt 4: Ergebnis anzeigen

- `AnalysisResultPanel` rendert nach `status='completed'`
- Felder: `summary`, `key_points[]`, `suggested_tags[]`, `suggested_topics[]`, `confidence` (0–1)
- API: `GET /api/v1/analysis/results/:id`

---

## Schritt 5: Zur Prüfung einreichen

- `btn-mark-for-review` — nur sichtbar bei `status='draft'`
- `POST /api/v1/analysis/results/:id/review` → `status: 'review'`
- Kein Admin erforderlich — jedes Workspace-Mitglied kann einreichen

---

## Schritt 6: Freigabe (Workspace-Admin)

- `btn-approve` und `btn-reject` — nur sichtbar für Workspace-Admin (`actor_role='admin'`)
- **Approve:** `POST /results/:id/approve` mit `{ confirm: true }` (Pflichtfeld) → `status: 'approved'`
  - `approved_by` und `approved_at` werden gesetzt
  - 8-Regel-`AnalysisApprovalPolicy` wird ausgeführt
- **Reject:** `POST /results/:id/reject` mit `{ reason: string }` → `status: 'rejected'`
- Fehlerverhalten: `confirm=False` → 400/409/422; Member → 403 (PROHIBIT-08)

---

## Schritt 7: In Wissensbasis importieren

- `btn-import` — **nur sichtbar wenn `status='approved'`** (Import-Guard Contract)
- `POST /api/v1/analysis/results/:id/import`
- Response: `ImportStats` mit 9 Feldern:

| Feld | Bedeutung |
|------|-----------|
| `result_id` | Quell-Ergebnis-UUID |
| `tags_created` | Neu angelegte Tags |
| `tags_found` | Bereits existierende Tags (unverändert) |
| `document_tags_applied` | Eingetragene document_tags (source='ki') |
| `topics_created` | Neu angelegte Topics (status='draft') |
| `topics_found` | Bereits existierende Topics |
| `topic_docs_attached` | Verknüpfte topic_documents |
| `topic_tags_applied` | Verknüpfte topic_tags |
| `source_document_count` | Anzahl Quelldokumente |

KB-Effekte: `tags` (find-or-create), `document_tags` (upsert, source='ki'), `topics` (slug-based, status='draft'), `topic_documents`, `topic_tags`.

**Idempotent:** Zweiter Import erzeugt keine Duplikate (created=0, found=N).

**Topics landen immer in status='draft'** — kein Auto-Approve (PROHIBIT-08 analog).

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
