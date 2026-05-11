# M4 Stabilization Sprint — Exit Criteria

Stand: 2026-05-11

Zweck: Dieses Dokument definiert die harten, maschinell pruefbaren Mindestbedingungen fuer den Abschluss des M4 Stabilization Sprint. Alle Kriterien muessen gleichzeitig erfuellt sein, bevor M4 freigegeben oder M5 gestartet werden darf.

Der verbindliche Validator ist `scripts/validate_m4_truth_gate.py`.
Der verbindliche Report ist `reports/postgres_truth_report.json`.

---

## 1. PostgreSQL Truth Suite

Quelle: `reports/postgres_truth_report.json` — Felder `passed`, `failed`, `errors`, `skipped`, `collected`, `pytest_exit_code`, `test_database_url_set`

| Bedingung | Pflichtwert | Beschreibung |
|---|---|---|
| `test_database_url_set` | `true` | Kein echter PostgreSQL-Nachweis ohne gesetzte DB-URL |
| `failed` | `0` | Kein einziger Testfehler toleriert |
| `errors` | `0` | Kein Setup-/Collect-Fehler toleriert |
| `skipped` | `0` | Kein Skip toleriert bei gesetzter DB-URL |
| `passed` | `== collected` | Jeder gesammelte Test muss bestanden haben |
| `pytest_exit_code` | `0` | Pytest-Prozess muss sauber beenden |

Verletzung einer dieser Bedingungen → `M4 Stabilization Gate = FAIL`.

---

## 2. Gate Scores

Quelle: `reports/postgres_truth_report.json` — Feld `gate_scores`

Der Gate Score pro Marker wird berechnet als:
`(Anzahl bestandene Tests mit diesem Marker / Anzahl gesammelte Tests mit diesem Marker) * 100`

| Gate | Marker | Mindestscore | Scope |
|---|---|---|---|
| M4a | `@pytest.mark.m4a_gate` | >= 95% | Auth, Workspace-Isolation, Membership-Scoping |
| M4b | `@pytest.mark.m4b_gate` | >= 90% | Upload-Vertrag, Job-Polling, Fehlerbehandlung |
| M4c | `@pytest.mark.m4c_gate` | >= 90% | Lifecycle, Search/Chat-Retrieval-Konsistenz |
| M4d | `@pytest.mark.m4d_gate` | >= 85% | Read-only Diagnostics (kein mutierender Admin-Pfad) |

Liegt der Score eines Gates unter dem Schwellenwert → `M4 Stabilization Gate = FAIL`.

Fehlen Tests fuer `m4d_gate` vollstaendig, erzeugt der Validator eine Warnung.
Fuer M4a, M4b und M4c ist eine leere Markergruppe ein harter Fehler.

---

## 3. RC-Blocker

Quelle: `reports/postgres_truth_report.json` — Feld `rc_blockers_open`

Jeder RC-Blocker ist einem kanonischen Testfall zugeordnet. Ein Blocker gilt als offen, wenn sein kanonischer Test nicht in `passed_tests` enthalten ist (fehlgeschlagen, uebersprungen oder nicht gelaufen).

| Blocker | Kanonischer Test |
|---|---|
| Race Condition | `test_chaos_advisory_lock_document_import_scope_blocks_concurrent_session` |
| Cross-Workspace Leak | `test_m4a_user_a_cannot_import_into_workspace_b` |
| Dead-Letter Replay Verlust | `test_chaos_dead_letter_replay_blocks_concurrent_session` |
| source_status Inkonsistenz | `test_chaos_source_status_live_lookup_reflects_lifecycle_transitions` |

Jeder offene RC-Blocker → `M4 Stabilization Gate = FAIL`.

---

## 4. Dokumentationsanforderungen

Diese Bedingungen werden nicht automatisch geprueft, muessen aber vor M4-Freigabe manuell bestaetigt werden:

| Bedingung | Pruefung |
|---|---|
| Keine unbelegten gruenen Aussagen in Doku und Masterplan | Manuell: alle ✅-Eintraege muessen auf einen gruenen Truth-Test oder einen Code-Nachweis zeigen |
| Masterplan referenziert `reports/postgres_truth/latest.json` | Manuell: Abschnitt "Aktueller Scope-Stand" nennt Commit-Hash und Zeitpunkt des letzten gruenen Runs |
| `docs/m4-m5-freigabefassung.md` ist aktuell | Manuell: der Stand muss mit dem letzten Report uebereinstimmen |

---

## 5. M5-Blockierung

M5 bleibt blockiert, solange mindestens eine der folgenden Bedingungen gilt:

1. `scripts/validate_m4_truth_gate.py` gibt Exit-Code != 0 zurueck.
2. Ein RC-Blocker ist offen (auch wenn der Validator aus anderen Gruenden PASS meldet).
3. Die manuelle Dokumentationspruefung ist nicht abgeschlossen.

Die Blockierung wird nicht durch manuelle Scores, Einschaetzungen oder unvollstaendige Laeufe aufgehoben.

---

## 6. Validator-Ausfuehrung

```powershell
# Neuen Report erzeugen und sofort validieren
scripts\run-m4-truth-gate.ps1

# Nur gegen bestehenden Report validieren
scripts\validate-m4-truth-gate.ps1
```

Ausgabe bei Erfolg:
```
M4 Stabilization Gate = PASS
Alle Exit-Kriterien erfüllt. M5-Freigabe kann geprüft werden.
```

Ausgabe bei Fehler:
```
M4 Stabilization Gate = FAIL
  N Exit-Kriterien nicht erfüllt:
  - [truth] failed must be 0, got 2
  - [gate_scores] M4a: 88.0% < 95.0%
  - [rc_blocker] offen: Dead-Letter Replay Verlust

M5 bleibt blockiert.
```

---

## 7. Versionierung und Traceability

Jeder Validator-Lauf erzeugt:

| Datei | Zweck |
|---|---|
| `reports/postgres_truth/YYYYMMDD_HHMMSS.json` | Unveraenderte Archivkopie dieses Laufs |
| `reports/postgres_truth/latest.json` | Zeiget immer auf den letzten Lauf |
| `reports/postgres_truth_report.json` | Flat-Kopie fuer Rueckwaertskompatibilitaet |
| `reports/postgres_truth_report.md` | Lesbare Zusammenfassung mit Gate Scores und RC-Blockern |
| `reports/postgres_truth_delta.md` | Vergleich gegen den vorherigen Lauf (Regression/Improvement) |

Eine M4-Freigabe darf nur auf Basis eines Laufs mit:
- `test_database_url_set: true`
- `commit_hash` aus dem aktuellen Hauptbranch
- Zeitpunkt nicht aelter als 24 Stunden vor der Freigabeentscheidung

ausgesprochen werden.
