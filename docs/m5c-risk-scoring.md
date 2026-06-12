# M5c Risk Scoring — Cleanup Kandidaten

**Status:** DEFINITION  
**Datum:** 2026-06-12  
**Gültig für:** CleanupCandidate.risk_score (0–100)

---

## Score-Klassen

| Klasse | Bereich | Bedeutung |
|--------|---------|-----------|
| `LOW` | 0–20 | Kein wesentliches Risiko. Kandidat kann in regulärem Batch bearbeitet werden. |
| `MEDIUM` | 21–40 | Moderates Risiko. Review empfohlen, kein Eskalationsbedarf. |
| `HIGH` | 41–60 | Erhöhtes Risiko. Manueller Review vor Proposal-Erstellung erforderlich. |
| `VERY_HIGH` | 61–80 | Hohes Risiko. Senior-Review + explizites PO-Sign-off pro Kandidat. |
| `CRITICAL` | 81–100 | Kritisches Risiko. Keine automatische Proposal-Generierung erlaubt. Nur manuell. |

---

## Scoring-Kriterien

Score = gewichtete Summe der 5 Kriterien (je 0–20 Punkte).

### 1. Datenverlust-Risiko (0–20)

Wie hoch ist die Wahrscheinlichkeit, dass die Aktion irreversiblen Datenverlust verursacht?

| Punkte | Indikator |
|--------|-----------|
| 0–4 | Entität hat keine referenzierten Inhalte, Kopie existiert |
| 5–9 | Entität hat geringe Inhaltsrelevanz, kein aktiver Zugriff |
| 10–14 | Entität enthält einzigartige Inhalte, aber keine aktiven Referenzen |
| 15–19 | Entität mit einzigartigen Inhalten und historischen Referenzen |
| 20 | Entität ist primäre Quelle mit aktiven Referenzen und keiner Kopie |

**Treiber:** `entity_type = document`, Content-Hash-Uniqueness, Versions-Count

### 2. Referenz-Risiko (0–20)

Wie viele andere Entitäten referenzieren den Kandidaten?

| Punkte | Indikator |
|--------|-----------|
| 0–4 | 0 eingehende Referenzen |
| 5–9 | 1–3 eingehende Referenzen, alle in anderen Workspaces |
| 10–14 | 4–10 eingehende Referenzen |
| 15–19 | 11–50 eingehende Referenzen |
| 20 | >50 eingehende Referenzen oder Referenz aus aktivem Index |

**Treiber:** Anzahl `citation`-Einträge, Chunk-Referenzen, aktive Query-Treffer

### 3. Retrieval-Risiko (0–20)

Würde eine Cleanup-Aktion laufende Retrieval-Ergebnisse beeinträchtigen?

| Punkte | Indikator |
|--------|-----------|
| 0–4 | Entität nie im Retrieval-Index (lifecycle_status=DRAFT) |
| 5–9 | Entität im Index, aber <10 Queries in letzten 30 Tagen |
| 10–14 | Entität im Index, 10–100 Queries in letzten 30 Tagen |
| 15–19 | Entität im Index, >100 Queries in letzten 30 Tagen |
| 20 | Entität ist Top-K-Ergebnis für bekannte kritische Queries |

**Treiber:** Query-Log-Frequenz, Retrieval-Index-Status, lifecycle_status

### 4. Lifecycle-Risiko (0–20)

Wie kritisch ist der aktuelle Lifecycle-Status der Entität?

| Punkte | Indikator |
|--------|-----------|
| 0–4 | `lifecycle_status = ARCHIVED` oder `DRAFT` |
| 5–9 | `lifecycle_status = INACTIVE` |
| 10–14 | `lifecycle_status = ACTIVE`, geringe Nutzung |
| 15–19 | `lifecycle_status = ACTIVE`, reguläre Nutzung |
| 20 | `lifecycle_status = ACTIVE`, kritischer Business-Prozess |

**Treiber:** `documents.lifecycle_status`, `import_status`, Nutzungsfrequenz

### 5. Governance-Risiko (0–20)

Welche regulatorischen oder Compliance-Anforderungen gelten für die Entität?

| Punkte | Indikator |
|--------|-----------|
| 0–4 | Keine bekannte Governance-Anforderung |
| 5–9 | Interne Richtlinie (Retention < 1 Jahr) |
| 10–14 | Interne Richtlinie (Retention > 1 Jahr) |
| 15–19 | Externe Anforderung (DSGVO, GxP, ISO) |
| 20 | Gesetzliche Aufbewahrungspflicht (HGB, DSGVO Art. 17 Ausnahmen) |

**Treiber:** Dokument-Metadaten (Kategorie, Tags), Workspace-Governance-Config

---

## Score-Berechnung

```
risk_score = datenverlust + referenz + retrieval + lifecycle + governance
           = sum(0..20) + sum(0..20) + sum(0..20) + sum(0..20) + sum(0..20)
           = 0..100
```

Klassen-Mapping:
```python
def classify(score: int) -> str:
    if score <= 20:   return "LOW"
    if score <= 40:   return "MEDIUM"
    if score <= 60:   return "HIGH"
    if score <= 80:   return "VERY_HIGH"
    return "CRITICAL"
```

---

## Klassen-Aktionsregeln

| Klasse | Automatische Proposal-Generierung | Pflicht-Review |
|--------|----------------------------------|----------------|
| LOW | erlaubt | optional |
| MEDIUM | erlaubt | empfohlen |
| HIGH | erlaubt | Pflicht |
| VERY_HIGH | erlaubt mit Flag | Senior + PO |
| CRITICAL | **verboten** | ausschließlich manuell |

**CRITICAL-Kandidaten** werden im Report gelistet, aber kein `CleanupProposal` wird automatisch erzeugt. Nur manueller PO-Trigger ist erlaubt.

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt |
