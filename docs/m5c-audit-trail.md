# M5c Cleanup Audit Trail

**Status:** DEFINITION  
**Datum:** 2026-06-12  
**Invariante:** Audit-Einträge sind unveränderbar und nicht löschbar

---

## Zweck

Der Audit Trail dokumentiert jeden CleanupRun lückenlos. Er dient der Nachvollziehbarkeit von Cleanup-Entscheidungen und ist Pflichtbestandteil für Compliance-Nachweise (DSGVO Art. 5, interne Governance).

---

## Schema: cleanup_audit_entry

| Feld | Typ | Nullable | Beschreibung |
|------|-----|----------|-------------|
| `id` | UUID | nein | Primärschlüssel, systemgeneriert |
| `run_id` | UUID | nein | FK → `CleanupRun.id` |
| `user` | varchar(255) | nein | User-ID oder System-Token des Auslösers |
| `workspace` | UUID | nein | Workspace-ID (redundant gespeichert für Audit-Isolation) |
| `candidate_count` | integer | nein | Anzahl erkannter Kandidaten |
| `risk_score_avg` | numeric(5,2) | nein | Durchschnittlicher Risk Score des Runs |
| `risk_score_max` | integer | nein | Maximaler Risk Score des Runs |
| `critical_count` | integer | nein | Anzahl CRITICAL-Kandidaten |
| `created_at` | timestamptz | nein | Erzeugungszeitpunkt (DB-seitig gesetzt, nicht überschreibbar) |
| `run_status` | varchar(20) | nein | COMPLETED oder FAILED (aus CleanupRun) |
| `proposals_generated` | integer | nein | Anzahl erzeugter Proposals |
| `dry_run` | boolean | nein | Immer `true` in M5c |
| `schema_version` | integer | nein | Audit-Schema-Version (aktuell: 1) |

---

## Unveränderlichkeits-Regeln

1. **INSERT-only:** Kein UPDATE oder DELETE auf `cleanup_audit`. Enforcement über DB-Trigger oder Row-Level Security.
2. **`created_at` ist DB-seitig gesetzt:** `DEFAULT NOW()`, kein Application-Override.
3. **Keine Soft-Delete-Spalte:** Kein `deleted_at`, kein `is_active`. Ein Eintrag existiert oder existiert nicht.
4. **Historisierung:** Ältere Einträge dürfen nie überschrieben werden, auch nicht bei Re-Runs.
5. **Retention:** Mindest-Aufbewahrung 7 Jahre (anpassbar via Governance-Config).

---

## Pflicht-Trigger

Ein Audit-Eintrag wird erzeugt:
- Bei jedem Abschluss eines CleanupRun (status=COMPLETED)
- Bei jedem FAILED-CleanupRun
- Bei jeder manuellen Proposal-Genehmigung (APPROVED)
- Bei jeder Proposal-Ablehnung (REJECTED)

---

## Abfrage-Patterns (read-only)

```sql
-- Alle Runs für einen Workspace, neueste zuerst
SELECT * FROM cleanup_audit
WHERE workspace = :workspace_id
ORDER BY created_at DESC;

-- Runs mit CRITICAL-Kandidaten
SELECT * FROM cleanup_audit
WHERE critical_count > 0
ORDER BY created_at DESC;

-- Audit-Statistik (Monat)
SELECT DATE_TRUNC('month', created_at) AS month,
       COUNT(*) AS runs,
       SUM(candidate_count) AS total_candidates,
       AVG(risk_score_avg) AS avg_risk
FROM cleanup_audit
GROUP BY 1
ORDER BY 1 DESC;
```

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt |
