# M5c Cleanup Governance Boundary

**Status:** DRAFT — Ratifizierung erst möglich wenn M5c Start Gate = PASS  
**Dokument-Typ:** Governance-Definition (keine Implementierung)  
**Datum:** 2026-06-12  
**Invariante:** Drift Detection darf nur erkennen, nie korrigieren (PROHIBIT-02, PROHIBIT-06)

---

## 1. Geltungsbereich

Dieses Dokument definiert die Governance-Grenze zwischen Drift Detection (M5b) und zukünftigen Cleanup-Operationen (M5c). Es legt fest, was M5b dauerhaft nicht tut, was M5c tun darf (sobald freigegeben), und unter welchen Bedingungen Cleanup-Aktionen zulässig werden.

---

## 2. Permanente Verbote (M5b — unveränderlich)

Die folgenden Aktionen sind in M5b dauerhaft verboten. Sie können nicht durch Konfiguration, Feature-Flag oder Nutzer-Aktion entsperrt werden.

### PROHIBIT-02: Keine Repair-Aktionen

| Verboten | Begründung |
|----------|-----------|
| Automatische Korrektur von Drift-Findings | Drift Detection ist ein Erkennungssystem, kein Reparatursystem |
| Schreiben in `documents`-Tabelle durch Drift-Detektoren | Read-only-Invariante |
| PUT/PATCH auf `/api/drift/*`-Endpunkten | Nicht implementiert, nicht erlaubt |
| Repair-Buttons im DriftDashboard | Verletzt UI-Constraint (kein Schreibzugriff aus Dashboard) |
| `lifecycle_status`-Änderungen durch Drift-Jobs | Zustandsänderungen sind Domäne von M5c, nicht M5b |

### PROHIBIT-06: Keine Cleanup-Aktionen

| Verboten | Begründung |
|----------|-----------|
| Löschen von als "stale" markierten Dokumenten | Keine destruktiven Operationen in M5b |
| Auto-Reindex nach Drift-Erkennung | Trigger für Schreiboperationen nicht erlaubt |
| Cleanup-Workflows aus Drift-Findings ableiten | M5b produziert Befunde, nicht Aktionen |
| Cleanup-Buttons im DriftDashboard | Verletzt UI-Constraint |
| Batch-Löschung von Dokumenten mit `lifecycle_status=ARCHIVED` | Nicht Bestandteil von M5b |

---

## 3. Erlaubte Aktionen in M5b (Bestätigung)

M5b darf ausschließlich folgende Operationen durchführen:

- `SELECT`-Queries auf `documents`-Tabelle (read-only)
- Drift-Findings schreiben in `drift_findings`-Tabelle (Erkennungsprotokoll)
- Drift-Run-Metadaten schreiben in `drift_runs`-Tabelle
- GET-Endpunkte bereitstellen: `/api/drift/status`, `/api/drift/findings`, `/api/drift/summary`
- Metriken emittieren (observability, kein PII)
- Dashboard darstellen (read-only, keine Aktionsbuttons)

---

## 4. Governance-Grenze M5b → M5c

```
M5b (Drift Detection)          M5c (Cleanup — NOCH NICHT FREIGEGEBEN)
─────────────────────          ─────────────────────────────────────────
Erkennt Drift                  Entscheidet über Repair
Produziert Findings            Konsumiert Findings (als Input)
Read-only auf documents        Darf documents schreiben (nach Freigabe)
Kein DELETE/PUT/PATCH          Darf DELETE/PUT/PATCH (nach PO-Sign-off)
Kein Auto-Trigger              Explizite manuelle Auslösung (geplant)
                               
        Grenze: M5c darf NICHT aus M5b-Code aufgerufen werden.
        M5c liest Findings aus der DB. Keine direkte Kopplung.
```

### Schnittstellenregel

M5c konsumiert `drift_findings` aus der Datenbank. Es gibt keine direkte Code-Abhängigkeit M5b → M5c. M5b-Code darf M5c-Module weder importieren noch aufrufen.

---

## 5. Freigabebedingungen für M5c

M5c darf erst implementiert werden, wenn **alle** der folgenden Bedingungen erfüllt sind:

| Bedingung | Aktueller Status |
|-----------|-----------------|
| M5c Start Gate = PASS | BLOCKED |
| M5b Production Readiness Gate = PASS | BLOCKED |
| M5b Beta Validation Gate = PASS | BLOCKED |
| M5b Alpha Hardening Gate = PASS | BLOCKED |
| Dieses Governance-Dokument ratifiziert (PO-Sign-off) | DRAFT |

**Aktuell: Alle Bedingungen NICHT erfüllt. M5c bleibt NO_GO.**

---

## 6. Ratifizierungsprozess

1. M5c Start Gate erreicht Status PASS (alle SG-01 bis SG-05 erfüllt)
2. PO (Markus Dickscheit) prüft dieses Dokument
3. PO signiert `cleanup_governance_boundary.json` (Feld `po_sign_off: true`)
4. Dokument-Status wechselt von DRAFT → RATIFIED
5. M5c-Implementierung darf beginnen

Ohne expliziten PO-Sign-off bleibt M5c NO-GO, auch wenn alle technischen Gates PASS erreichen.

---

## 7. Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt (Task 37, M5b-Pipeline) |
