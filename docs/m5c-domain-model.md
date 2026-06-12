# M5c Cleanup Domain Model

**Status:** DEFINITION — Keine Implementierung. M5c bleibt NO_GO bis Start Gate = PASS.  
**Datum:** 2026-06-12  
**Invariante:** Drift Detection darf nur erkennen, nie korrigieren (PROHIBIT-02, PROHIBIT-06)  
**Gültig ab:** Erst nach PO-Sign-off auf `cleanup_governance_boundary.json`

---

## Entitäten-Übersicht

```
CleanupSnapshot ──┐
                  │
CleanupRun ───────┼──► CleanupCandidate (1:N)
                  │         │
                  └──► CleanupProposal (1:N, je Candidate)
```

---

## CleanupSnapshot

Punkt-in-Zeit-Abbild des Workspace-Zustands zum Zeitpunkt eines CleanupRun. Wird aus `drift_findings` der M5b-Pipeline befüllt — nie direkt aus `documents`.

| Feld | Typ | Nullable | Beschreibung |
|------|-----|----------|-------------|
| `id` | UUID | nein | Primärschlüssel |
| `workspace_id` | UUID | nein | Workspace-Scope |
| `created_at` | timestamptz | nein | Erstellungszeitpunkt |
| `source_drift_run_id` | UUID | ja | FK → `drift_runs.id` (M5b-Herkunft) |
| `document_count` | integer | nein | Anzahl Dokumente im Snapshot |
| `findings_count` | integer | nein | Anzahl Drift-Findings als Basis |
| `snapshot_data` | jsonb | nein | Serialisierter Workspace-Zustand |

**Regeln:**
- Snapshot wird beim Start eines CleanupRun erzeugt (nie nachträglich mutiert)
- `source_drift_run_id` muss auf einen abgeschlossenen Drift Run verweisen
- Kein direktes Lesen aus `documents` — ausschließlich aus `drift_findings`

---

## CleanupRun

Ausführungseinheit einer Cleanup-Analyse. Erzeugt Kandidaten und Proposals, führt aber selbst keine Datenänderungen durch.

| Feld | Typ | Nullable | Beschreibung |
|------|-----|----------|-------------|
| `id` | UUID | nein | Primärschlüssel |
| `workspace_id` | UUID | nein | Workspace-Scope |
| `status` | enum | nein | `PENDING \| RUNNING \| COMPLETED \| FAILED` |
| `created_at` | timestamptz | nein | Erstellungszeitpunkt |
| `started_at` | timestamptz | ja | Beginn der Ausführung |
| `completed_at` | timestamptz | ja | Abschluss |
| `triggered_by` | enum | nein | `SYSTEM \| USER` |
| `snapshot_id` | UUID | ja | FK → `CleanupSnapshot.id` |
| `candidates_found` | integer | nein | Anzahl erzeugter Kandidaten |
| `proposals_generated` | integer | nein | Anzahl erzeugter Proposals |
| `error_message` | text | ja | Fehlermeldung bei `FAILED` |

**Status-Übergänge:**
```
PENDING → RUNNING → COMPLETED
                  ↘ FAILED
```

**Regeln:**
- Ein CleanupRun darf keine Schreiboperationen auf `documents` auslösen
- `candidates_found` wird erst bei `COMPLETED` gesetzt
- Ein FAILED-Run darf nicht wiederholt werden — neuer Run erforderlich

---

## CleanupCandidate

Einzelner Befund eines CleanupRun. Beschreibt eine Entität, die für Cleanup in Frage kommt. Keine Aktion — nur Datenstruktur.

| Feld | Typ | Nullable | Beschreibung |
|------|-----|----------|-------------|
| `id` | UUID | nein | Primärschlüssel |
| `workspace_id` | UUID | nein | Workspace-Scope |
| `cleanup_run_id` | UUID | nein | FK → `CleanupRun.id` |
| `candidate_type` | enum | nein | Typ des Kandidaten (siehe unten) |
| `severity` | enum | nein | `LOW \| MEDIUM \| HIGH \| CRITICAL` |
| `entity_type` | varchar(64) | nein | Typ der betroffenen Entität (z.B. `document`, `chunk`) |
| `entity_id` | UUID | nein | ID der betroffenen Entität |
| `reason` | text | nein | Maschinenlesbare Begründung |
| `risk_score` | integer | nein | 0–100 (gemäß Risk Scoring Modell) |
| `remediation_hint` | text | ja | Empfohlene Aktion (informativ, nicht ausführend) |
| `detected_at` | timestamptz | nein | Zeitpunkt der Erkennung |
| `evidence` | jsonb | ja | Strukturierte Belege (z.B. duplicate_ids, orphan_refs) |

### Candidate Types

| Typ | entity_type | Beschreibung |
|-----|------------|-------------|
| `DUPLICATE_DOCUMENT` | `document` | Dokument mit identischem oder hochähnlichem Inhalt zu einem anderen |
| `DUPLICATE_VERSION` | `document_version` | Versionsduplikat innerhalb desselben Dokuments |
| `ORPHAN_CHUNK` | `chunk` | Chunk ohne referenzierendes Dokument |
| `ORPHAN_VERSION` | `document_version` | Version ohne parent-Dokument |
| `ORPHAN_CITATION` | `citation` | Zitat-Referenz auf nicht-existente Quelle |
| `UNUSED_METADATA` | `metadata_entry` | Metadaten-Eintrag ohne zugehöriges Dokument |

**Regeln:**
- `risk_score` muss im Bereich 0–100 liegen (Validation beim Schreiben)
- `entity_id` muss eine existierende Entität referenzieren (zur Erkennungszeit)
- `remediation_hint` ist informativ — kein Trigger für automatische Aktionen
- Ein Kandidat ist unveränderlich nach Erstellung (`INSERT`-only)

---

## CleanupProposal

Formaler Vorschlag zur Behandlung eines CleanupCandidate. Wartet auf menschliche Entscheidung (`APPROVED` / `REJECTED`). Ausführung erst nach explizitem PO-Trigger — nicht Teil von M5c-Definition.

| Feld | Typ | Nullable | Beschreibung |
|------|-----|----------|-------------|
| `id` | UUID | nein | Primärschlüssel |
| `cleanup_run_id` | UUID | nein | FK → `CleanupRun.id` |
| `candidate_id` | UUID | nein | FK → `CleanupCandidate.id` |
| `proposed_action` | enum | nein | `DELETE \| MERGE \| ARCHIVE \| FLAG` |
| `status` | enum | nein | `PENDING \| APPROVED \| REJECTED \| EXECUTED` |
| `created_at` | timestamptz | nein | Erstellungszeitpunkt |
| `reviewed_at` | timestamptz | ja | Zeitpunkt der menschlichen Entscheidung |
| `reviewed_by` | varchar(255) | ja | Entscheider (User-ID oder System-Token) |
| `execution_result` | jsonb | ja | Ergebnis nach Ausführung (nur bei `EXECUTED`) |
| `rejection_reason` | text | ja | Begründung bei `REJECTED` |

**Status-Übergänge:**
```
PENDING → APPROVED → EXECUTED
        ↘ REJECTED
```

**Proposed Actions:**

| Aktion | Beschreibung |
|--------|-------------|
| `DELETE` | Entität löschen (erfordert höchste Autorisierung) |
| `MERGE` | Duplikat in primäre Entität zusammenführen |
| `ARCHIVE` | Entität als archiviert markieren (kein Löschen) |
| `FLAG` | Zur manuellen Prüfung markieren (keine Datenänderung) |

**Regeln:**
- `EXECUTED` ist nur nach `APPROVED` erreichbar
- `EXECUTED` setzt `execution_result` — niemals leer
- Ein `REJECTED` Proposal kann nicht reaktiviert werden
- Kein Proposal darf ohne menschliche Genehmigung in `EXECUTED` übergehen (No-Auto-Execute)

---

## Beziehungen

```
CleanupRun (1) ──────────────────── (0..1) CleanupSnapshot
CleanupRun (1) ──────────────────── (0..N) CleanupCandidate
CleanupRun (1) ──────────────────── (0..N) CleanupProposal
CleanupCandidate (1) ──────────── (0..1) CleanupProposal
```

Ein Kandidat hat maximal einen Proposal pro Run. Ein Proposal referenziert genau einen Kandidaten.

---

## Abgrenzung zu M5b

| Aspekt | M5b (Drift Detection) | M5c (Cleanup) |
|--------|-----------------------|---------------|
| Liest `documents` | ja (read-only) | via Snapshot |
| Schreibt `drift_findings` | ja | nein |
| Schreibt `cleanup_candidates` | nein | ja |
| Schreibt `cleanup_proposals` | nein | ja |
| Ändert `documents` | nein | nur nach APPROVED + EXECUTED |
| Ausführung | automatisch (geplant) | nur nach PO-Sign-off |

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt (M5c Domain Model Definition) |
