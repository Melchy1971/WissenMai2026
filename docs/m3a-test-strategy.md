# M3a GUI Foundation - Teststrategie und Governance-Integration

Stand: 2026-05-18

Ziel dieser Teststrategie ist, die GUI von M3a nicht nur gegen den API-Contract abzusichern, sondern sie verbindlich in Truth-, Drift-, Recovery-, Contract- und Security-Governance einzubetten.

Leitprinzipien:

- Die GUI bleibt read-only.
- Tests pruefen Anzeige, Mapping und Fehlertransparenz, nicht Backend-Reparatur.
- Fehlercodes muessen sichtbar bleiben.
- Mocking darf den API-Contract simulieren, aber nicht veraendern.
- `reports/frontend_truth_report.json` ist Pflichtartefakt fuer produktionsnahe GUI-Aussagen.
- GUI-Regressionen sind gate-relevant, wenn sie Nutzerfluesse, Error States, Recovery-Pfade oder Drift-Sichtbarkeit betreffen.
- Frontend-Drift darf nicht still bleiben; degradierte oder unklare Zustandslagen muessen sichtbar sein.
- Ein fokussierter Testlauf belegt nur einen Teilscope, niemals den Gesamtzustand von M3a.

## Governance-Integration

M3a respektiert verbindlich folgende Governance-Dokumente:

- Truth-Governance: `docs/operational-truth-governance.md`
- Drift-Governance: `docs/drift.md`
- Recovery-Governance: `docs/controlled-failure-philosophy.md`, `docs/frontend-offline-degraded-strategy.md`, `docs/frontend-runtime-state-machine.md`
- Contract-Governance: `docs/api/frontend-backend-contract-registry.md`
- Security-Governance: `docs/security.md`

### Integrationsregeln

1. M3a darf keinen grünen oder stabilisierten Zustand aus Dokumentation, lokaler Beobachtung oder isolierten Komponententests ableiten.
2. Frontend Truth Reports sind Pflichtartefakte; ohne aktuellen `reports/frontend_truth_report.json` bleibt der Status `unknown`, `partial` oder `fail`.
3. Contract-Stabilitaet ist Pflicht. Ein grüner Frontend-Lauf kompensiert keinen roten Contract-Report.
4. Recovery-Flows wie API down, Retry, Reconnect, Restore-Mode und sichtbare Error States sind Teil der Pflichtabdeckung von M3a.
5. Security-Flows wie Auth Required, Forbidden, Workspace-Isolation, Route Guards, Logout und Session-Kontext sind gate-relevant, sobald M3a produktionsnahe GUI-Aussagen treffen will.
6. Frontend-Drift muss sichtbar sein. Search Drift, Queue degraded, Restore, Reindex, Retrieval Regression, Backup-Staleness und Cleanup Dry Run duerfen nicht verdeckt bleiben, wenn der Slice sie betrifft oder konsumiert.

## Neue Gate-Regeln fuer M3a

M3a darf nur dann als `pass`, `stabilisiert` oder `operational bereit` beschrieben werden, wenn alle folgenden Bedingungen gleichzeitig erfuellt sind:

- `reports/frontend_truth_report.json` ist aktuell, maschinenlesbar und weist `passed = collected`, `failed = 0`, `skipped = 0` und `exit_code = 0` aus
- `reports/contract_test_report.json` ist gruen
- ein integrierter Gate-Report wie `reports/m3a_gate_result.json` weist keine Blocker aus
- GUI-Regressionen in den Pflichtslices Auth, Workspace, Documents, Search, Chat, Upload, Lifecycle und Diagnostics sind null oder als nicht-scope dokumentiert
- sichtbare Drift-Hinweise werden nicht unterdrueckt oder auf gruen gemappt
- Recovery-Pfade sind sichtbar, testbar und widersprechen nicht der Runtime-State-Machine
- Security-relevante Frontend-Flows haben einen aktuellen Truth-Nachweis fuer den beanspruchten Scope

Wenn eine dieser Bedingungen fehlt:

- `fail`, wenn ein Pflichtartefakt rot ist oder eine Pflichtbedingung verletzt ist
- `unknown`, wenn ein Pflichtartefakt fehlt
- `partial`, wenn nur ein fokussierter Slice belegt ist

## Frontend Truth Policies

### Pflichtregeln

1. `reports/frontend_truth_report.json` ist Pflichtartefakt fuer GUI-Readiness und Regression-Bewertung.
2. GUI-Regressionen sind gate-relevant und duerfen nicht als kosmetisch herabgestuft werden, wenn sie sichtbare Kernpfade betreffen.
3. Ein lokaler Vitest-, Storybook- oder Mock-Lauf darf einen roten Frontend-Truth-Report nicht ueberstimmen.
4. Frontend-Truth-Berichte muessen Auth-, Workspace- und API-Kontext offenlegen, wenn daraus Freigabeaussagen abgeleitet werden.
5. Frontend-Drift ist sichtbar zu machen: degraded Banner, Warning-Modelle, Statusindikatoren und Stale-Hinweise sind Teil der GUI-Wahrheit.

### Gate-relevante GUI-Regressionen

Diese Regressionen blockieren M3a mindestens auf `fail` oder `watch`, solange kein explizit begrenzter Scope dokumentiert ist:

- Auth-Bootstrap bricht oder zeigt keinen sichtbaren Error State
- Workspace-Bootstrap liefert keinen konsistenten aktiven Workspace
- API down, Forbidden oder Retry-Flow verletzt die Error-State-Regeln
- Search-, Chat-, Upload- oder Lifecycle-Kernfluss ist unbenutzbar oder verdeckt Fehler
- Diagnostics- oder Drift-Warnoberflaeche fehlt, obwohl Backend-Signale vorliegen
- Restore-, Reconnect- oder degraded-Zustaende wirken wie Normalbetrieb oder leere Datenlage

### Frontend Drift Policy

- Frontend Drift ist jede sichtbare Abweichung zwischen betrieblichem Zustand und gerenderter UI-Wahrheit.
- M3a darf keinen degradierte, stale oder unklaren Zustand als gesund darstellen.
- Unbekannte oder unbelegte Zustandslagen werden konservativ als `warning`, `unknown` oder `not_verified` behandelt, nie als `ok`.
- Diagnostics und fachnahe Screens muessen Drift-Signale sichtbar halten, auch wenn noch kein separater Frontend-Drift-Report existiert.

## Testmatrix

| Testart | Fokus | Zielobjekte | Werkzeug | Erfolgsnachweis |
|---|---|---|---|---|
| Unit Tests | ViewModel-Mapping und Fehlerabbildung | Mapper, `ImportStatusVM`, `ErrorVM` | `Vitest` | API-Felder werden korrekt in ViewModels ueberfuehrt, Fallbacks greifen deterministisch |
| Component Tests | Darstellung einzelner UI-Bausteine | Dokumentliste, Dokumentdetail, Chunkliste, State-Komponenten | `Vitest` + `@testing-library/react` | Komponenten rendern Daten, Leerzustaende und Fehlerzustaende korrekt |
| API Mock Tests | Verhalten gegen erfolgreiche und fehlerhafte API-Responses | Pages und API-Client | `Vitest` + Fetch-Mocks oder `msw` | `200`, `404`, `409` und API-down werden sichtbar und korrekt behandelt |
| E2E Smoke Test | Minimaler End-to-End-Nutzungsfluss | Dokumentliste, Detail, Chunk-Vorschau | spaeter Playwright oder Cypress | Kernflow laeuft im Browser gegen ein lauffaehiges Backend oder stabile Mocks |

## 1. Unit Tests

### Scope

- `DocumentListItemVM`
- `DocumentDetailVM`
- `VersionListItemVM`
- `ChunkListItemVM`
- `ImportStatusVM`
- `ErrorVM`

### Konkrete Testfaelle

1. `DocumentListItemVM mappt vollständige API-Daten korrekt`
   - Input: vollstaendiges Objekt aus `GET /documents`
   - Erwartung: alle Anzeige-Felder gesetzt, Status `chunked -> Lesbar`

2. `DocumentListItemVM setzt Fallbacks bei optionalen Feldern`
   - Input: `mime_type = null`, `latest_version_id = null`
   - Erwartung: `mimeType = unbekannt`, `latestVersionId = null`

3. `DocumentDetailVM mappt Dokumentdetail inklusive Summary`
   - Input: vollstaendiger `GET /documents/{id}`-Response plus Versionen und Chunks
   - Erwartung: Meta-Felder, Status, Versionen und Chunkzahlen korrekt im VM

4. `DocumentDetailVM behandelt pending ohne Version`
   - Input: `import_status = pending`, `latest_version = null`, `parser_metadata = null`
   - Erwartung: kein Crash, `hasReadableVersion = false`, Status bleibt sichtbar

5. `VersionListItemVM markiert aktuelle Version`
   - Input: Versionsobjekt plus `latestVersionId`
   - Erwartung: genau ein VM mit `isLatest = true`

6. `ChunkListItemVM mappt Vorschau und Quellenanker`
   - Input: Chunk mit teilweisem `source_anchor`
   - Erwartung: `sourceAnchorLabel` bleibt darstellbar, fehlende Teilwerte brechen nicht

7. `ImportStatusVM mappt bekannte Status korrekt`
   - Inputs: `pending`, `parsed`, `chunked`, `failed`, `duplicate`
   - Erwartung: korrektes Label, Tone und Readability-Flag

8. `ImportStatusVM fällt auf unknown zurück`
   - Input: leerer oder unbekannter Status
   - Erwartung: `kind = unknown`, `label = Unbekannt`

9. `ErrorVM mappt API-Fehlercodes korrekt`
   - Inputs: `WORKSPACE_REQUIRED`, `DOCUMENT_NOT_FOUND`, `DOCUMENT_STATE_CONFLICT`, `SERVICE_UNAVAILABLE`
   - Erwartung: Titel, Severity und Debug-Code stimmen

10. `ErrorVM mappt Netzwerkfehler als API down`
    - Input: `NETWORK_ERROR`
    - Erwartung: sichtbarer Fehlercode und Retry-Hinweis

### Akzeptanzkriterien fuer Unit Tests

- Alle sechs ViewModel-Gruppen sind mindestens einmal direkt getestet.
- Fallbacks fuer `null`, leere Strings und unbekannte Status sind abgedeckt.
- Kein Mapper wirft bei gueltigen, aber unvollstaendigen Paket-5-Responses einen Fehler.

## 2. Component Tests

### Scope

- Dokumentliste
- Dokumentdetail
- Chunkliste
- Statuskomponenten fuer Loading, Empty, Error

### Konkrete Testfaelle

1. `Dokumentliste rendert Tabelle mit Datensätzen`
   - Erwartung: Titel, Statusbadge, Versions- und Chunkanzahl sichtbar

2. `Dokumentliste rendert Leerzustand`
   - Input: leeres Array
   - Erwartung: Text `Keine Dokumente vorhanden`

3. `Dokumentliste rendert Fehlerzustand mit Code`
   - Input: `ErrorVM` mit `SERVICE_UNAVAILABLE`
   - Erwartung: Titel, Message und Fehlercode sichtbar

4. `Dokumentdetail rendert Metadaten und Status`
   - Erwartung: Dokumenttitel, MIME-Typ, Parser-Version, Importstatus sichtbar

5. `Dokumentdetail rendert pending ohne Version robust`
   - Erwartung: Status sichtbar, kein Absturz, keine falsche Versionsanzeige

6. `Chunkliste rendert Vorschautext und Quellenanker`
   - Erwartung: `positionLabel`, `textPreview`, `sourceAnchorLabel` sichtbar

7. `Chunkliste rendert leere Vorschau robust`
   - Input: leerer `text_preview`
   - Erwartung: Fallback `Keine Vorschau verfuegbar`

8. `ErrorState zeigt Fehlercode immer sichtbar`
   - Erwartung: Debug-Code steht im gerenderten Screen-State

### Akzeptanzkriterien fuer Component Tests

- Dokumentliste, Dokumentdetail und Chunkliste sind jeweils direkt abgedeckt.
- Leer-, Lade- und Fehlerzustand sind fuer mindestens einen Screen nachgewiesen.
- Keine Komponente verschluckt den Fehlercode oder ersetzt ihn durch rein dekorative Texte.

## 3. API Mock Tests

### Scope

- Erfolgreiche Responses
- `404`
- `409`
- API down

### Konkrete Testfaelle

1. `GET /documents erfolgreich`
   - Mock: `200` mit Dokumentliste
   - Erwartung: Liste rendert dokumentierte Felder

2. `GET /documents leer`
   - Mock: `200` mit `[]`
   - Erwartung: Leere Dokumentliste sichtbar, kein Fehlerzustand

3. `GET /documents API down`
   - Mock: Netzwerkfehler oder `503`
   - Erwartung: `API nicht erreichbar` oder `Service nicht verfuegbar`, Fehlercode sichtbar

4. `GET /documents/{id} erfolgreich`
   - Mock: `200` mit Detailobjekt
   - Erwartung: Metadaten, Versionen und Chunk-Vorschau koennen weitergeladen werden

5. `GET /documents/{id} 404`
   - Mock: `404 DOCUMENT_NOT_FOUND`
   - Erwartung: Detailscreen zeigt sichtbaren Fehlercode und keine Scheindaten

6. `GET /documents/{id} 409`
   - Mock: `409 DOCUMENT_STATE_CONFLICT`
   - Erwartung: Konfliktzustand sichtbar, keine normale Detailansicht vortaeuschen

7. `GET /documents/{id}/versions erfolgreich`
   - Mock: `200` mit Versionsarray
   - Erwartung: Historie sichtbar, aktuelle Version markierbar

8. `GET /documents/{id}/chunks erfolgreich`
   - Mock: `200` mit Chunk-Vorschau
   - Erwartung: Vorschautext und Quellenanker sichtbar

9. `GET /documents/{id}/chunks API down`
   - Mock: Netzwerkfehler
   - Erwartung: sichtbarer Fehlerzustand, kein stilles Leer-Rendering

### Akzeptanzkriterien fuer API Mock Tests

- Die vier Response-Klassen `200`, `404`, `409`, `API down` sind fuer M3a mindestens einmal pruefbar dokumentiert.
- Mock-Tests arbeiten nur mit dokumentierten Paket-5-Feldern.
- Kein Test setzt Mutation, Upload, Suche oder Chat voraus.

## 4. E2E Smoke Test

### Ziel

- Minimaler Browser-Nachweis, dass der Kernfluss der M3a-GUI zusammenhaengend funktioniert.

### Smoke Flow

1. Dokumentliste oeffnen
   - Route: `/documents?workspace_id=<test-workspace>`
   - Erwartung: Liste oder definierter Leerzustand sichtbar

2. Dokumentdetail oeffnen
   - Aktion: erstes Dokument aus der Liste anklicken
   - Erwartung: Detailscreen mit sichtbarem Dokumenttitel und Statusbadge

3. Chunks anzeigen
   - Erwartung: Chunk-Vorschau im Detailscreen sichtbar oder eindeutig leer dokumentiert

### Konkrete Smoke-Testfaelle

1. `Smoke: Dokumentliste lädt und zeigt Einträge`
2. `Smoke: Klick auf Dokument öffnet Detailscreen`
3. `Smoke: Detailscreen zeigt Versionen und Chunk-Vorschau`
4. `Smoke: Fehlercode bleibt sichtbar, wenn Detailroute ein 404 liefert`

### Akzeptanzkriterien fuer den E2E Smoke Test

- Der Kernflow Liste -> Detail -> Chunk-Vorschau ist im Browser nachweisbar.
- Der Smoke Test fuehrt keine Schreiboperation aus.
- Fehlerfaelle werden als sichtbare UI-Zustaende gezeigt, nicht als leere oder gebrochene Screens.

## Empfohlene Dateistruktur fuer Tests

```text
frontend/src/tests/
  api/
    documents.test.jsx
  view-models/
    mappers.test.jsx
    error.test.jsx
    import-status.test.jsx
  components/
    DocumentTable.test.jsx
    DocumentMetaCard.test.jsx
    ChunkPreviewList.test.jsx
    ErrorState.test.jsx
  pages/
    DocumentsPage.test.jsx
    DocumentDetailPage.test.jsx
  e2e/
    m3a-smoke.spec.ts
```

## Mindestabnahme fuer M3a-Testreife

- Unit Tests decken ViewModel-Mapping und Fehlerabbildung ab.
- Component Tests decken Dokumentliste, Dokumentdetail und Chunkliste ab.
- API Mock Tests decken `200`, `404`, `409` und API down ab.
- Ein E2E Smoke Test deckt den Kernflow Liste -> Detail -> Chunks ab.
- Fehlercode bleibt in allen Fehlerbildern fuer Debugging sichtbar.