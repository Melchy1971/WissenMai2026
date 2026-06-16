# Export Center — Spezifikation

**Stand:** 2026-06-15 | **Status:** NICHT_BEGONNEN (Implementierung ausstehend)
**Priorität:** P2 | **Voraussetzung:** RC Gate = RELEASE_CANDIDATE

---

## Überblick

Das Export Center ermöglicht den strukturierten Datenexport aus Ruflo in drei Formaten (PDF, Markdown, JSON) aus drei Quellbereichen (Themen, Dokumente, Analyseergebnisse). Jeder Export erzeugt ein Audit-Event und ist strikt workspace-isoliert.

---

## Exportarten

### PDF-Export

**Verwendungszweck:** Druckfähige Berichte, Weitergabe ohne Ruflo-Zugang.

**Inhalte:**
- Dokumenttitel, Metadaten (Quelle, Importdatum, Lifecycle-Status)
- Volltext des normalisierten Markdown (aus `document_versions.normalized_markdown`)
- Tags mit Quelle (`manual`, `ki`, `import`) und Konfidenz
- Themenbezüge (aus `analysis_results.suggested_topics`)
- Quellenangaben bei Analyseergebnissen (Dokument-IDs werden als Dokumenttitel aufgelöst, keine technischen IDs)
- Seitenformat: A4, Schriftgröße 11pt, Kopfzeile mit Workspace-Name und Exportdatum

**Nicht im PDF:**
- Interne IDs, Job-IDs, Chunk-IDs
- Gate-Status, Report-Pfade, technische Metadaten
- Andere Workspace-Inhalte

### Markdown-Export

**Verwendungszweck:** Weiterbearbeitung, Archivierung, Versionierung in Git.

**Inhalte:**
- YAML-Frontmatter: `title`, `exported_at`, `source_workspace` (Name, nicht ID), `tags`, `topics`
- Dokumentkörper: normalisiertes Markdown ohne Änderungen
- Bei Analyseergebnissen: Sections für `summary`, `key_points`, `suggested_tags`, `suggested_topics`, `confidence`
- Quellenangaben als Markdown-Fußnoten

**Dateiname-Konvention:** `{dokumenttitel_slug}_{YYYYMMDD}.md`

### JSON-Export

**Verwendungszweck:** Maschinenlesbare Weiterverarbeitung, Backup, Migration.

**Schema:**
```json
{
  "export_schema_version": 1,
  "exported_at": "ISO8601",
  "source": "ruflo",
  "workspace_name": "...",
  "export_type": "document|topic|analysis_result",
  "items": [ ... ]
}
```

**Item-Schema (Dokument):**
```json
{
  "title": "...",
  "source_type": "...",
  "mime_type": "...",
  "lifecycle_status": "active|archived",
  "imported_at": "ISO8601",
  "content_markdown": "...",
  "tags": [{"name": "...", "source": "manual|ki|import", "confidence": 0.95}],
  "topics": ["..."],
  "versions_count": 1
}
```

Nicht im JSON-Export: `id`, `workspace_id`, `content_hash`, `chunk_id`, Job-IDs.

---

## Quellen

### 1. Themen (Topics)

- Exportiert: Themenname, zugeordnete Dokumente (Titel), Analysejobs die dieses Thema erzeugt haben (Datum, Typ), Top-Tags
- Abhängigkeit: `/topics`-CRUD-API muss implementiert sein (aktuell NICHT_BEGONNEN, Gap AGAP-07)
- Interim: Export aus `analysis_results.suggested_topics` möglich, aber unvollständig

### 2. Dokumente

- Exportiert: Einzeldokument oder Dokument-Batch (max. 50 Dokumente pro Export)
- Filter: nach Lifecycle-Status, Tag, Importdatum
- Versionierung: exportiert aktuelle Version (`current_version_id`)
- Mehrfachdokument-Export: ZIP-Archiv mit Einzeldateien + `manifest.json`

### 3. Analyseergebnisse

- Exportiert: Job-Metadaten (Typ, Datum), Result (summary, key_points, suggested_tags, suggested_topics, confidence), Comparison (overlaps, differences, suggested_merge), genehmigte Suggestions
- Quellenangaben: Quell-Dokumente werden mit Titel aufgelöst
- Keine Rohdaten aus Chunks (kein Dokumentinhalt in Analyse-Exports)

---

## Technische Anforderungen

### Workspace Isolation

- Jeder Export-Aufruf muss `workspace_id` aus dem Auth-Context ziehen (`require_workspace_member`)
- Keine Cross-Workspace-Referenzen in Export-Inhalten
- Exportierte Dokument-IDs werden vor Ausgabe entfernt oder zu Titeln aufgelöst
- Batch-Exports dürfen nur Dokumente aus demselben Workspace enthalten

### Audit Events

Jeder Export-Vorgang erzeugt ein Audit-Event:

| Feld | Wert |
|---|---|
| `event_type` | `export_created` |
| `workspace_id` | aus Auth-Context |
| `user_id` | aus Auth-Context |
| `export_type` | `pdf`, `markdown`, `json` |
| `source_type` | `document`, `topic`, `analysis_result` |
| `item_count` | Anzahl exportierter Elemente |
| `timestamp` | UTC |

Audit-Events werden in der bestehenden Audit-Infrastruktur (`/audit`) gespeichert.

---

## API-Design (Ziel)

```
POST /api/v1/export/documents        — Dokument(e) exportieren
POST /api/v1/export/topics           — Themen exportieren
POST /api/v1/export/analysis-results — Analyseergebnisse exportieren
GET  /api/v1/export/jobs/:id         — Export-Job-Status (bei großen Batches)
GET  /api/v1/export/jobs/:id/download — Download der fertigen Datei
```

**Request-Schema:**
```json
{
  "format": "pdf|markdown|json",
  "item_ids": ["..."],
  "include_content": true,
  "include_tags": true,
  "include_topics": true,
  "include_sources": true
}
```

**Auth:** `require_workspace_member` für alle Export-Endpunkte.

---

## Nicht im Scope

- Export von Drift-Findings oder Data-Quality-Findings (kein Nutzer-Kontext)
- Export von Rohdaten (Chunks, Search-Vektoren)
- Technische IDs (job_id, workspace_id, chunk_id) in exportierten Inhalten
- Gate-Daten, Report-Pfade, interne Statuswerte
- Automatisierte / geplante Exports (Post-1.0)
- Export über E-Mail oder externe Speicherdienste (Post-1.0)

---

## Implementierungsreihenfolge

1. JSON-Export für Dokumente (einfachste Form, kein Rendering)
2. Markdown-Export für Dokumente
3. Audit-Event-Integration
4. Analyseergebnisse JSON-Export
5. PDF-Rendering (Bibliothek: `weasyprint` oder `reportlab`)
6. Themen-Export (abhängig von Topics-CRUD-API)
7. Batch-Export (ZIP)

---

*evaluation_method: static_code_analysis | generated_at: 2026-06-15*
