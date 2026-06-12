# M5c Candidate Detection Rules

**Status:** DEFINITION  
**Datum:** 2026-06-12  
**Invariante:** Detection ist read-only — keine Datenänderung durch Detection-Lauf

---

## Regel 1: DUPLICATE_DOCUMENT

**Definition:** Zwei oder mehr Dokumente im selben Workspace haben identischen oder hochähnlichen Inhalt (content_hash-Match oder Similarity ≥ 0.95).

**SQL-Quelle:**
```sql
SELECT a.id AS entity_id, b.id AS duplicate_of,
       a.workspace_id, a.content_hash
FROM documents a
JOIN documents b
  ON a.workspace_id = b.workspace_id
 AND a.content_hash = b.content_hash
 AND a.id <> b.id
 AND a.lifecycle_status NOT IN ('ARCHIVED', 'DELETED')
WHERE a.id < b.id  -- deduplizieren
```

**Detection-Strategie:** Content-Hash-Vergleich als primäre Methode. Fuzzy-Matching (Similarity ≥ 0.95) als sekundäre Methode für nahezu-identische Inhalte.

**Risiko:** Datenverlust bei Merge, falls Duplikat unterschiedliche Metadaten oder Annotations trägt.

**Reporting:** `candidate_type=DUPLICATE_DOCUMENT`, `evidence={duplicate_of: <id>, similarity: 1.0}`, `severity` aus Risk Score.

---

## Regel 2: DUPLICATE_VERSION

**Definition:** Zwei Versionen desselben Dokuments haben identischen Inhalt (content_hash-Match).

**SQL-Quelle:**
```sql
SELECT v1.id AS entity_id, v2.id AS duplicate_of,
       v1.document_id, v1.workspace_id
FROM document_versions v1
JOIN document_versions v2
  ON v1.document_id = v2.document_id
 AND v1.content_hash = v2.content_hash
 AND v1.id <> v2.id
 AND v1.version_number > v2.version_number
```

**Detection-Strategie:** Intra-Dokument Hash-Vergleich. Nur aufeinanderfolgende Versionen oder alle Versionspaare (konfigurierbar).

**Risiko:** Niedrig — Versionsduplikate haben meist keinen Verlust-Impact. Erhöht sich wenn Version explizit referenziert wird.

**Reporting:** `candidate_type=DUPLICATE_VERSION`, `entity_type=document_version`, `evidence={document_id, version_a, version_b}`.

---

## Regel 3: ORPHAN_CHUNK

**Definition:** Ein Chunk existiert ohne referenzierendes Dokument (FK-Verletzung oder gelöschtes Parent-Dokument).

**SQL-Quelle:**
```sql
SELECT c.id AS entity_id, c.workspace_id
FROM chunks c
LEFT JOIN documents d ON c.document_id = d.id
WHERE d.id IS NULL
   OR d.lifecycle_status = 'DELETED'
```

**Detection-Strategie:** LEFT JOIN auf `documents`. NULL-Result oder DELETED-Status gilt als Orphan.

**Risiko:** Moderat — Orphan Chunks belegen Speicher im Vector-Index, können Retrieval-Ergebnisse verfälschen.

**Reporting:** `candidate_type=ORPHAN_CHUNK`, `entity_type=chunk`, `remediation_hint="Chunk ohne parent document — prüfe ob document gelöscht wurde"`.

---

## Regel 4: ORPHAN_VERSION

**Definition:** Eine Dokumentversion existiert ohne referenzierendes Dokument.

**SQL-Quelle:**
```sql
SELECT v.id AS entity_id, v.workspace_id
FROM document_versions v
LEFT JOIN documents d ON v.document_id = d.id
WHERE d.id IS NULL
```

**Detection-Strategie:** LEFT JOIN auf `documents`. Fehlender Parent gilt als Orphan.

**Risiko:** Niedrig bis moderat — abhängig davon, ob die Version im Retrieval-Index vorhanden ist.

**Reporting:** `candidate_type=ORPHAN_VERSION`, `entity_type=document_version`.

---

## Regel 5: ORPHAN_CITATION

**Definition:** Eine Citation (Quellenangabe) referenziert ein nicht-existentes oder gelöschtes Dokument.

**SQL-Quelle:**
```sql
SELECT ci.id AS entity_id, ci.workspace_id
FROM citations ci
LEFT JOIN documents d ON ci.source_document_id = d.id
WHERE d.id IS NULL
   OR d.lifecycle_status = 'DELETED'
```

**Detection-Strategie:** LEFT JOIN auf `documents` via `source_document_id`. Prüft auch auf DELETED-Status.

**Risiko:** Moderat — kann Retrieval-Antworten mit Broken-Links korrumpieren. Governance-Risiko wenn regulatorisch relevante Quellen betroffen.

**Reporting:** `candidate_type=ORPHAN_CITATION`, `entity_type=citation`, `evidence={source_document_id, last_known_title}`.

---

## Regel 6: UNUSED_METADATA

**Definition:** Ein Metadaten-Eintrag (z.B. Tag, Label, Custom-Attribute) ist keinem existierenden Dokument zugeordnet.

**SQL-Quelle:**
```sql
SELECT m.id AS entity_id, m.workspace_id
FROM document_metadata m
LEFT JOIN documents d ON m.document_id = d.id
WHERE d.id IS NULL
```

**Detection-Strategie:** LEFT JOIN auf `documents`. Fehlende Zuordnung gilt als unused.

**Risiko:** Niedrig — kein Datenverlust, aber Speicher-Overhead und potenzielle Schema-Inkonsistenz.

**Reporting:** `candidate_type=UNUSED_METADATA`, `entity_type=metadata_entry`, `severity=LOW` (default).

---

## Gemeinsame Detection-Regeln

- Alle Queries laufen read-only (`SELECT` only, kein DML)
- Workspace-Scope wird immer als Filter angewendet (`WHERE workspace_id = :workspace_id`)
- Detection-Ergebnisse werden in `cleanup_candidates` geschrieben (nicht in `documents`)
- Bei Fehler: Partial Results mit `status=PARTIAL`, kein Abbruch des gesamten Runs
- Keine automatische Proposal-Erzeugung für `CRITICAL`-Kandidaten

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt |
