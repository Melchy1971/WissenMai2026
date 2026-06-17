# Product Maturity Delta — PRI-5 → PRI-6

Stand: 2026-06-17

---

## Gesamtscore

| Version | Score | Schwellwert CONDITIONAL_RC | Schwellwert GA |
|---------|-------|---------------------------|----------------|
| PRI-5 (Formel v4) | 76 | 76 | 85 |
| PRI-6 (Formel v5, 11 Dim.) | **80** | 80 | 85 |
| Delta | **+4** | neue Schwelle | — |

_PRI-6 verwendet eine neue 11-Dimensionen-Formel (Gleichgewichtung). Vergleich mit PRI-5 ist methodisch bedingt nicht direkt linear._

---

## Änderungen je Dimension (PRI-6 Formel)

| Dimension | PRI-6 Score | Delta | Ursache |
|-----------|------------|-------|---------|
| Dokumente | 85 | 0 | Unverändernd |
| Suche | 45 | 0 | Kein KWIC, kein Stemming — GA-FUNC-01 |
| Themen | 80 | 0 | Unverändernd |
| Analyse | 86 | +1 | Kleinere Qualitätsverbesserungen |
| **Approval** | **92** | **+2** | AdminRoute-Guard (SCGB-03) → SH-05 vollständig PASS |
| Export | 80 | 0 | Unverändernd |
| Dashboard | 68 | 0 | W06 fehlt weiterhin — GA-UX-01 |
| **Security** | **84** | **+9** | SCGB-03 geschlossen, 6 SH-Bereiche nun vollständig bewertet |
| **Tests** | **89** | **+2** | AdminRouteGuard.test.jsx (3 Tests) ergänzt |
| **Betrieb** | **87** | **+2** | SCG-05 PASS nach Router-Guard-Fix |
| **Dokumentation** | **84** | **+2** | blocking_matrix, warning_disposition, rc_limitations, ga_backlog, release_notes |

---

## Verbleibende Schwächen

**Suche (Score 45)** ist die größte Einzelschwäche. Ohne KWIC, Stemming und Tag-Filter liegt diese Dimension weit unter dem Durchschnitt und zieht den Gesamtscore um ~3 Punkte.

**Dashboard (Score 68):** W06 Drift-Widget fehlt. Systemzustand nicht kompakt sichtbar.

---

## Hebel für nächste +5 Punkte (Richtung GA-Schwellwert 85)

| Maßnahme | Aufwand | Erwarteter Score-Gewinn |
|----------|---------|------------------------|
| Suche 45→85 (KWIC+Stemming+Tags) | 3–5 Tage | +3.6 Gesamtpunkte |
| Dashboard 68→85 (W06 Widget) | 1–2 Tage | +1.5 Gesamtpunkte |
| Security 84→90 (CSP) | 0.5 Tag | +0.5 Gesamtpunkte |

Summe: ca. **+5.6 Punkte** → GA-Schwellwert 85 erreichbar nach PRI-7.
