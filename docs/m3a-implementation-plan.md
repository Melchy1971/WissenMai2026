# M3a GUI Foundation - Implementierungsplan

Stand: 2026-05-04

Annahmen:

- Backend Paket 5 ist abgeschlossen. Quelle: `reports/current/masterplan_status.json`.
- Der API-Contract fuer die Dokument-Read-Pfade ist stabil.
- Die GUI bleibt in M3a strikt read-only.

Ziel:

- Eine belastbare, kleine Web-GUI bauen, die den Backend-Zustand sichtbar macht, ohne Suche, Chat oder Mutation einzufuehren.

## 1. Tech Stack

Festlegung fuer M3a:

- Build und Dev Server: `Vite`
- UI Framework: `React`
- Sprache fuer neue M3a-Dateien: `TypeScript`
- Routing: `react-router-dom`
- API-Zugriff: `fetch` ueber schmale Frontend-API-Schicht
- State-Modell: lokaler React-State pro Screen plus kleine Shared-Helfer, kein globales State-Framework in M3a
- ViewModel-Mapping: eigene Mapper unter `src/view-models`
- Tests:
  - Unit- und Mapping-Tests: `Vitest`
  - Komponenten-/Screen-Tests: `@testing-library/react`
  - Browser-API-Mocking: `msw` oder einfacher Fetch-Mock, je nach Minimalitaet

Begruendung:

- Das bestehende Frontend ist bereits `React` + `Vite`.
- M3a braucht Routing, API-Client, Mapping und Tests, aber noch keinen schweren globalen Client-State.
- Neue M3a-Arbeit sollte in `TypeScript` erfolgen, damit die ViewModel-Schicht und der API-Contract sauber typisiert sind.

## 2. Zielstruktur im Frontend

Empfohlene Struktur fuer M3a:

```text
frontend/
  src/
    api/
      client.ts
      documents.ts
      errors.ts
    app/
      App.tsx
      AppShell.tsx
      routes.tsx
    components/
      status/
        ErrorState.tsx
        EmptyState.tsx
        LoadingState.tsx
        StatusBadge.tsx
      documents/
        DocumentListTable.tsx
        DocumentMetaCard.tsx
        VersionList.tsx
        ChunkList.tsx
    pages/
      DocumentsPage.tsx
      DocumentDetailPage.tsx
      DocumentVersionsPage.tsx
      DocumentChunksPage.tsx
      DocumentStatusPage.tsx
    view-models/
      document-list-item.ts
      document-detail.ts
      version-list-item.ts
      chunk-list-item.ts
      import-status.ts
      error.ts
      mappers.ts
    types/
      api.ts
      ui.ts
    tests/
      api/
      view-models/
      pages/
      components/
    lib/
      date-format.ts
      route-builders.ts
      constants.ts
    styles/
      global.css
    main.tsx
```

Hinweise:

- Bestehende Ordner `features/` koennen fuer spaetere Fachfeatures bleiben, M3a selbst sollte aber ueber die klaren technischen Schichten `api`, `pages`, `components`, `view-models` aufgebaut werden.
- Bestehende `jsx`-Dateien koennen als Startpunkt ersetzt oder parallel schrittweise nach `tsx` migriert werden.

## 3. Routing

Empfohlenes M3a-Routing:

| Route | Screen | Zweck |
|---|---|---|
| `/` | Redirect auf Dokumentuebersicht | eindeutiger Einstieg |
| `/documents` | Dokumentuebersicht | Liste aller Dokumente eines Workspaces |
| `/documents/:documentId` | Dokumentdetail | Dokumentzustand und Summary |
| `/documents/:documentId/versions` | Versionsansicht | Read-only Versionshistorie |
| `/documents/:documentId/chunks` | Chunk-Ansicht | Read-only Chunks der aktuellen Version |
| `/documents/:documentId/status` | Fehler-/Importstatus-Ansicht | einheitliche Status- und Fehlerdarstellung |

Routing-Regeln:

- `workspace_id` wird in M3a zunaechst als Query-Parameter auf der Dokumentuebersicht gefuehrt.
- Fehlerhafte oder fehlende Routenparameter werden nicht still repariert.
- Fehlercodes bleiben im Zielscreen sichtbar.

## 4. API Client

### Aufgaben des API-Clients

- Basis-URL kapseln.
- Request-Aufbau fuer die vier Read-Endpunkte zentralisieren.
- Error-Envelope oder Netzwerkfehler in ein einheitliches Frontend-Fehlermodell ueberfuehren.
- Keine ViewModel-Logik im API-Client.

### Geplante API-Dateien

- `src/api/client.ts`
  - generischer `requestJson()`-Wrapper
  - HTTP-Status, JSON-Parsing und Fehlernormalisierung
- `src/api/documents.ts`
  - `getDocuments()`
  - `getDocumentDetail()`
  - `getDocumentVersions()`
  - `getDocumentChunks()`
- `src/api/errors.ts`
  - Mapping von Netzwerk-/HTTP-/Envelope-Fehlern in ein gemeinsames API-Fehlerobjekt

### API-Type-Schnitt

Die API-Schicht arbeitet gegen rohe API-Typen aus `src/types/api.ts`.

Beispielhafte Typgruppen:

- `DocumentListItemResponse`
- `DocumentDetailResponse`
- `DocumentVersionSummaryResponse`
- `DocumentChunkPreviewResponse`
- `ApiErrorEnvelope`

## 5. ViewModels

Quelle:

- Die verbindliche ViewModel-Spezifikation liegt in [docs/m3a-viewmodels.md](H:/WissenMai2026/docs/m3a-viewmodels.md).

### Geplante Frontend-Dateien

- `src/view-models/document-list-item.ts`
- `src/view-models/document-detail.ts`
- `src/view-models/version-list-item.ts`
- `src/view-models/chunk-list-item.ts`
- `src/view-models/import-status.ts`
- `src/view-models/error.ts`
- `src/view-models/mappers.ts`

### Mapper-Regeln

- API-Response rein, ViewModel raus.
- Fallbacks nur in Mappern, nicht in React-Komponenten.
- Datumsformatierung und Label-Bildung zentralisieren.
- `ImportStatusVM` und `ErrorVM` als Shared-Modelle fuer alle Screens verwenden.

## 6. Screens implementieren

### 6.1 Dokumentuebersicht

Dateien:

- `src/pages/DocumentsPage.tsx`
- `src/components/documents/DocumentListTable.tsx`

Aufgaben:

- `workspace_id`, `limit`, `offset` lesen.
- `GET /documents` aufrufen.
- `DocumentListItemVM[]` rendern.
- Leer-, Lade- und Fehlerzustand sauber anzeigen.

### 6.2 Dokumentdetail

Dateien:

- `src/pages/DocumentDetailPage.tsx`
- `src/components/documents/DocumentMetaCard.tsx`

Aufgaben:

- `GET /documents/{documentId}` aufrufen.
- `DocumentDetailVM` rendern.
- `import_status`, `latest_version`, `parser_metadata`, `chunk_summary` sichtbar machen.
- Konflikte nicht verstecken.

### 6.3 Versionsansicht

Dateien:

- `src/pages/DocumentVersionsPage.tsx`
- `src/components/documents/VersionList.tsx`

Aufgaben:

- `GET /documents/{documentId}/versions` aufrufen.
- `VersionListItemVM[]` rendern.
- Read-only Historie darstellen.

### 6.4 Chunk-Ansicht

Dateien:

- `src/pages/DocumentChunksPage.tsx`
- `src/components/documents/ChunkList.tsx`

Aufgaben:

- `GET /documents/{documentId}/chunks` aufrufen.
- `ChunkListItemVM[]` rendern.
- `text_preview` und `source_anchor` sichtbar machen.

### 6.5 Fehler-/Importstatus-Ansicht

Dateien:

- `src/pages/DocumentStatusPage.tsx`
- `src/components/status/ErrorState.tsx`
- `src/components/status/EmptyState.tsx`
- `src/components/status/LoadingState.tsx`
- `src/components/status/StatusBadge.tsx`

Aufgaben:

- Fehlercodes sichtbar ausgeben.
- `ImportStatusVM` und `ErrorVM` sauber darstellen.
- Keine Reparaturaktion anbieten.

## 7. Tests definieren

Verbindliche Detailstrategie:

- [M3a GUI Teststrategie](H:/WissenMai2026/docs/m3a-test-strategy.md)

### 7.1 API-Client-Tests

Pfad:

- `src/tests/api/`

Pruefen:

- korrekter Request-Aufbau
- Envelope-Parsing
- Netzwerkfehler -> `ErrorVM`-nahe Fehlerobjekte
- `503`, `404`, `409`, `422` werden nicht verschluckt

### 7.2 ViewModel-Mapping-Tests

Pfad:

- `src/tests/view-models/`

Pruefen:

- `DocumentListItemVM` Mapping
- `DocumentDetailVM` Mapping
- `VersionListItemVM` Mapping
- `ChunkListItemVM` Mapping
- `ImportStatusVM` Mapping
- `ErrorVM` Mapping
- Fallbacks bei `null` oder fehlenden Optionalfeldern

### 7.3 Komponenten- und Screen-Tests

Pfad:

- `src/tests/components/`
- `src/tests/pages/`

Pruefen:

- Dokumentliste zeigt Tabelle, Leerzustand und Fehlerzustand
- Dokumentdetail zeigt Status und Summary korrekt
- Versionsansicht rendert read-only Historie
- Chunk-Ansicht rendert Vorschautext und Quellenanker
- Fehlercode bleibt sichtbar

### 7.4 Minimale Vertragsabsicherung

Pruefen:

- Screens verwenden nur dokumentierte API-Felder
- keine Mutation in M3a-Komponenten
- kein Such-, Chat- oder Upload-Pfad wird versehentlich eingebaut

## Dateiuebersicht

Konkrete erste M3a-Dateien:

```text
frontend/src/main.tsx
frontend/src/app/App.tsx
frontend/src/app/AppShell.tsx
frontend/src/app/routes.tsx
frontend/src/api/client.ts
frontend/src/api/documents.ts
frontend/src/api/errors.ts
frontend/src/types/api.ts
frontend/src/types/ui.ts
frontend/src/view-models/document-list-item.ts
frontend/src/view-models/document-detail.ts
frontend/src/view-models/version-list-item.ts
frontend/src/view-models/chunk-list-item.ts
frontend/src/view-models/import-status.ts
frontend/src/view-models/error.ts
frontend/src/view-models/mappers.ts
frontend/src/pages/DocumentsPage.tsx
frontend/src/pages/DocumentDetailPage.tsx
frontend/src/pages/DocumentVersionsPage.tsx
frontend/src/pages/DocumentChunksPage.tsx
frontend/src/pages/DocumentStatusPage.tsx
frontend/src/components/status/ErrorState.tsx
frontend/src/components/status/EmptyState.tsx
frontend/src/components/status/LoadingState.tsx
frontend/src/components/status/StatusBadge.tsx
frontend/src/components/documents/DocumentListTable.tsx
frontend/src/components/documents/DocumentMetaCard.tsx
frontend/src/components/documents/VersionList.tsx
frontend/src/components/documents/ChunkList.tsx
frontend/src/tests/api/documents.test.ts
frontend/src/tests/view-models/mappers.test.ts
frontend/src/tests/pages/DocumentsPage.test.tsx
frontend/src/tests/pages/DocumentDetailPage.test.tsx
frontend/src/tests/pages/DocumentVersionsPage.test.tsx
frontend/src/tests/pages/DocumentChunksPage.test.tsx
```

## Reihenfolge

Empfohlene Implementierungsreihenfolge:

1. `Tech Stack und Baseline finalisieren`
   - `react-router-dom`, `@testing-library/react`, `@testing-library/jest-dom` und Mocking-Strategie festlegen.
   - `tsx`-Einstieg vorbereiten.

2. `App-Rahmen und Routing bauen`
   - `main.tsx`, `App.tsx`, `AppShell.tsx`, `routes.tsx`.

3. `API-Typen und API-Client bauen`
   - rohe Response-Typen
   - Request-Wrapper
   - Dokument-API-Funktionen

4. `ViewModels und Mapper bauen`
   - alle sechs ViewModels aus der M3a-Spezifikation
   - zentrale Mapping- und Fallback-Logik

5. `Status-Komponenten bauen`
   - Loading, Empty, Error, StatusBadge

6. `Dokumentuebersicht implementieren`
   - erster echter End-to-End-Screen der M3a-GUI

7. `Dokumentdetail implementieren`
   - inklusive Importstatus und Konfliktfaellen

8. `Versionsansicht implementieren`

9. `Chunk-Ansicht implementieren`

10. `Fehler-/Importstatus-Ansicht finalisieren`
   - gemeinsame Statuspolitik fuer alle Screens konsolidieren

11. `Tests nachziehen und haerten`
   - API-Client
   - ViewModels
   - Seitenzustandslogik

## Definition of Ready fuer Start der Implementierung

- Paket-5-Gate bleibt `>= 90`.
- Basis-Workspace fuer lokale GUI-Tests ist bekannt.
- API-Base-URL ist fuer lokale Entwicklung definiert.
- ViewModel-Spezifikation bleibt die alleinige Quelle fuer UI-Datenkopplung.

## Nicht-Ziele in diesem Plan

- Keine Suche.
- Kein Chat.
- Kein Upload.
- Keine Mutation.
- Keine Rollen- oder Rechteverwaltung.
- Keine OCR- oder Embedding-Funktionalitaet.
