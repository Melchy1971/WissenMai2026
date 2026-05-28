# GUI Truth Surface Model

Stand: 2026-05-18

Ziel: Die GUI darf niemals einen besseren Systemzustand suggerieren als tatsaechlich existiert. Jede Truth Surface ist eine sichtbare UI-Flaeche, die einen operativen, fachlichen oder systemischen Zustand transportiert. Diese Flaechen muessen konservativ, evidenzgebunden und degradationsfaehig modelliert werden.

Verbindliche Bezugsdokumente:

- `docs/frontend-strategic-principles.md`
- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-cache-governance.md`
- `docs/frontend-error-state-catalog.md`
- `docs/frontend-offline-degraded-strategy.md`
- `docs/operational-truth-governance.md`
- `docs/api/frontend-backend-contract-registry.md`
- `docs/m4d-admin-diagnostics.md`

## Truth Surface Modell

### Grundsatz

Eine Truth Surface darf nur den Zustand darstellen, der durch eine aktuelle, scope-korrekte und sichtbare Datenquelle belegt ist.

### Verbindliche Wahrheitsregeln

- Keine Truth Surface darf aus fehlender Evidenz einen `ok`-, `healthy`- oder Erfolgszustand ableiten.
- Jede Truth Surface braucht eine benannte echte Datenquelle oder einen expliziten `unknown`-Pfad.
- Vereinfachung ist erlaubt, wenn Bedeutung und Risikoklasse erhalten bleiben.
- Vereinfachung ist verboten, wenn aus `degraded`, `stale`, `unknown`, `retryable`, `failed` oder `maintenance` optisch ein Success-Zustand wird.
- Degraded, stale, retrying, restore, reindex und drift muessen sichtbar bleiben.
- Optimistic completion ohne abgeschlossenen Backend-Nachweis ist fuer operative Truth Surfaces verboten.
- Bei Konflikt zwischen Surface und Report gilt die maschinenlesbare Truth-Quelle.

## Truth Surfaces

### 1. Upload Status

Echte Datenquelle:

- `UploadJobResponse` aus `POST /documents/import` und `GET /api/v1/jobs/{job_id}`
- Felder: `status`, `progress_current`, `progress_total`, `progress_message`, `error_code`, `result`, `finished_at`

Erlaubte Vereinfachungen:

- technische Job-States auf lesbare UI-Labels wie `In Warteschlange`, `Wird verarbeitet`, `Abgeschlossen`, `Fehlgeschlagen` mappen
- `duplicate` als kontrollierten Endzustand sichtbar zusammenfassen

Verbotene Vereinfachungen:

- `completed` anzeigen, bevor ein Job-Endzustand aus der Job-Quelle vorliegt
- `duplicate`, `failed`, `retryable` oder `dead_letter` als normalen Erfolg darstellen
- Polling-Abbruch oder verlorene Verbindung als still abgeschlossenen Import darstellen

Degraded Darstellung:

- Queue- oder Upload-Degradierung zeigt Warnhinweis, blockiert Start oder markiert laufende Statusanzeige als eingeschraenkt
- Polling-Unsicherheit wird als `Status unbestaetigt` oder `stale` sichtbar

Unknown state handling:

- fehlt aktueller Jobstatus, bleibt die Surface `unknown` oder `Status nicht bestaetigt`
- kein Wechsel auf Erfolg nur wegen lokaler Datei-Auswahl oder Request-Start

### 2. Queue Status

Echte Datenquelle:

- aggregierte Queue-/Import-Signale aus `GET /api/v1/admin/diagnostics`
- Import-Aggregate, Queue-Aging- oder Dead-Letter-Hinweise aus Diagnostics/Observability

Erlaubte Vereinfachungen:

- Queue-Zustand als `gesund`, `degraded`, `kritisch` oder `unknown` in einer Surface verdichten
- mehrere interne Queue-Metriken zu einer sichtbaren Betriebsampel zusammenfassen, wenn `warning` und `critical` erhalten bleiben

Verbotene Vereinfachungen:

- fehlende Queue-Evidenz als `gesund` darstellen
- Upload-Flaechen aktiv lassen, obwohl Queue-Degradierung blockierend belegt ist
- Dead-Letter-, Starvation- oder Aging-Signale verstecken

Degraded Darstellung:

- sichtbarer Queue-Warnbanner oder Diagnostics-Indikator
- Upload-Start blockiert oder mit Warnhinweis versehen

Unknown state handling:

- kein Queue-Health-Nachweis bedeutet `unknown`, nicht `ok`
- fehlende Diagnosedaten muessen als unbelegt sichtbar bleiben

### 3. Search Availability

Echte Datenquelle:

- `GET /api/v1/search/chunks`
- Diagnostics- oder Health-Signale fuer Search-Index-Verfuegbarkeit

Erlaubte Vereinfachungen:

- Search auf `verfuegbar`, `eingeschraenkt`, `nicht verfuegbar` verdichten
- technische Fehlercodes in standardisierte Search-Error-States mappen

Verbotene Vereinfachungen:

- leere Trefferliste als Beleg fuer gesunde Search darstellen, wenn der Request technisch fehlgeschlagen ist
- stale Search Results als frische Search Availability ausgeben
- Search-Ausfall als global gesunden App-Zustand tarnen

Degraded Darstellung:

- Search-Panel zeigt lokalen Warn- oder Fehlerzustand
- alte Treffer bleiben nur read-only und stale sichtbar

Unknown state handling:

- ohne aktuellen erfolgreichen Search-Check ist Availability `unknown` oder `nicht bestaetigt`
- keine gruene Search-Surface aus historischem Cache

### 4. Retrieval Quality

Echte Datenquelle:

- Chat-Retrieval-Ergebnis aus `ChatMessageResponse.confidence`
- Retrieval-Regression- und Drift-Signale aus Diagnostics oder spaeterem Drift-Report

Erlaubte Vereinfachungen:

- Retrieval-Qualitaet auf `ausreichend`, `eingeschraenkt`, `unzureichend`, `unknown` abbilden
- `INSUFFICIENT_CONTEXT` als kontrollierten nicht-erfolgreichen Zustand darstellen

Verbotene Vereinfachungen:

- Assistant-Antwort ohne ausreichenden Kontext als voll belastbaren Retrieval-Erfolg darstellen
- fehlende Confidence oder degradierte Retrieval-Signale als normalen Chat-Erfolg zeigen
- Retrieval-Regression hinter einem normalen Erfolgscontainer verstecken

Degraded Darstellung:

- sichtbarer Hinweis auf eingeschraenkte Quellenbasis oder Retrieval-Regression
- Quellen bleiben sichtbar, aber als stale, archiviert oder unzureichend markiert

Unknown state handling:

- fehlt Confidence oder Diagnostik, ist Retrieval-Qualitaet `unknown`
- keine stillschweigende Aufwertung auf `gut`

### 5. Drift Status

Echte Datenquelle:

- `drift_awareness` aus `GET /api/v1/admin/diagnostics`
- spaetere maschinenlesbare Drift-Reports

Erlaubte Vereinfachungen:

- verschiedene Drift-Indikatoren in `info`, `warning`, `critical`, `unknown` verdichten
- Top-Banner plus Detailkarten verwenden

Verbotene Vereinfachungen:

- aktive Drift-Warnungen nur in tiefen Admin-Screens verstecken, wenn sie fachlich relevant sind
- unbelegte Drift-Signale als `kein Drift` darstellen
- fehlende Runtime-Signale fuer Restore/Reindex/Cleanup als gesund darstellen

Degraded Darstellung:

- Warn- oder Critical-Banner, Statuskarten, Stale-Indikatoren
- betroffene Features tragen lokale Hinweise zusaetzlich zum globalen Signal

Unknown state handling:

- fehlende Drift-Evidenz ergibt `unknown` oder `not_verified`
- `unknown` ist sichtbar als Warnzustand, nicht als `ok`

### 6. Restore Status

Echte Datenquelle:

- Runtime-State `restore_mode`
- Restore-Truth-Report oder Restore-Signale aus Diagnostics

Erlaubte Vereinfachungen:

- Restore als `aktiv`, `nicht aktiv`, `unknown` modellieren
- read-only Betriebsmodus prominent darstellen statt interne Schritte offenlegen zu muessen

Verbotene Vereinfachungen:

- normale Fachnutzung als gesund darstellen, waehrend Restore aktiv ist
- Restore-Ende behaupten, bevor Auth-, Workspace- und Cache-Neuvalidierung abgeschlossen sind Quelle: `reports/current/masterplan_status.json`.

Degraded Darstellung:

- globaler Restore-Banner, Read-only-Modus, blockierte Mutationen

Unknown state handling:

- wenn kein aktueller Restore-Nachweis vorliegt, keine aktive Gesundmeldung
- unbekannter Restore-Status bleibt `unknown` oder `not_verified`

### 7. Reindex Status

Echte Datenquelle:

- Search-Index-Job-/Diagnostics-Signale
- `SearchIndexRebuildJobResult` oder read-only Diagnostics-Hinweise

Erlaubte Vereinfachungen:

- Reindex auf `laeuft`, `nicht aktiv`, `unknown` verdichten
- Such- und Chat-Retrieval-Flaechen als `wird aktualisiert` markieren

Verbotene Vereinfachungen:

- Search als frisch markieren, waehrend Reindex aktiv oder unbelegt ist
- Reindex-Fortschritt oder Abschluss ohne Backend-Evidenz behaupten

Degraded Darstellung:

- Maintenance-Banner, stale Search- und Retrieval-Hinweise

Unknown state handling:

- fehlendes Reindex-Signal bleibt `unknown`
- kein stiller Wechsel auf `aktuell`

### 8. Lifecycle State

Echte Datenquelle:

- `DocumentListResponse.lifecycle_status`
- `DocumentDetailResponse.lifecycle_status`, `archived_at`, `deleted_at`
- `ChatCitationResponse.source_status`

Erlaubte Vereinfachungen:

- `active`, `archived`, `deleted` als klare Labels oder Badges abbilden
- historische Quellenzustaende in einfache Source-Status-Hinweise verdichten

Verbotene Vereinfachungen:

- archivierte oder geloeschte Objekte wie aktive Objekte aussehen lassen
- Lifecycle-Konflikte als normalen Dokumentzustand darstellen
- historische Citations ohne Source-Status-Hinweis rendern

Degraded Darstellung:

- archivierte, geloeschte oder fehlende Quellen sichtbar markieren
- Lifecycle-Konflikte als Fehler- oder Warnzustand zeigen

Unknown state handling:

- fehlt Lifecycle-Evidenz, bleibt die Surface `unknown`
- kein Default auf `active`

### 9. Backup Freshness

Echte Datenquelle:

- Backup-/Restore-Verify-Reports
- Diagnostics- oder Drift-Awareness-Signal fuer veraltetes Backup

Erlaubte Vereinfachungen:

- Backup-Frische auf `aktuell`, `warnend veraltet`, `kritisch veraltet`, `unknown` verdichten
- konkrete Zeitdeltas in lesbare Kategorien mappen

Verbotene Vereinfachungen:

- fehlenden Verify-Nachweis als `Backup aktuell` darstellen
- veraltete oder fehlgeschlagene Backups als neutralen Status zeigen

Degraded Darstellung:

- Warn- oder Critical-Hinweis mit Bezug auf Betriebsrisiko

Unknown state handling:

- ohne aktuellen Backup-/Verify-Nachweis ist der Status `unknown`
- kein Erfolg nur wegen Existenz eines historischen Reports

### 10. Diagnostics Health

Echte Datenquelle:

- `GET /api/v1/admin/diagnostics`
- Felder `system`, `database`, `counts`, `imports`, `search`, `auth`, `drift_awareness`

Erlaubte Vereinfachungen:

- Teilbereiche zu kompakten Statuskarten zusammenfassen
- `ok`, `degraded`, `error`, `unknown` als kanonische Anzeige verwenden

Verbotene Vereinfachungen:

- redigierte oder fehlende Checks als gesund darstellen
- stale Diagnostics ohne Kennzeichnung rendern
- unbekannte Zusatzfelder oder fehlende Teilchecks still ignorieren, wenn dadurch das Gesamtbild besser wirkt

Degraded Darstellung:

- sichtbare Statuskarten, Warnbanner, Detailindikatoren fuer Drift und Betriebsprobleme

Unknown state handling:

- einzelne fehlende Checks werden als `unknown` oder `not_verified` markiert
- Gesamtgesundheit darf nicht besser als der schlechteste relevante Teilzustand wirken

## UI-Wahrheitsregeln

### Regel 1: Surface vor Schmuck

- Eine Truth Surface ist kein Dekorationselement, sondern eine Betriebs- oder Fachaussage.
- Design darf Lesbarkeit verbessern, aber nicht Risikosignale abschwaechen.

### Regel 2: Kein besserer Zustand als die Quelle

- Die UI darf einen Zustand nur dann als `ok`, `ready`, `healthy`, `completed` oder `fresh` zeigen, wenn die echte Quelle genau diesen Zustand oder eine klar aequivalente Evidenz liefert.

### Regel 3: Unknown ist ein echter Zustand

- `unknown`, `not_verified` und `status unbestaetigt` sind gueltige UI-Zustaende.
- Fehlende Evidenz wird sichtbar gerendert, nicht weginferiert.

### Regel 4: Stale ist nicht fresh

- Read-only Cache-Nutzung ist erlaubt.
- Stale-Daten duerfen nie als frische operative Wahrheit ausgegeben werden.

### Regel 5: Completion braucht Nachweis

- `completed`, `success`, `healthy` und vergleichbare Abschlusszustaende brauchen einen Backend- oder Report-Nachweis.
- Lokale Nutzeraktion, Request-Dispatch oder optimistic UI reichen dafuer nicht.

### Regel 6: Lokale Fehler sind lokal sichtbar

- Feature-spezifische Degradierung bleibt lokal sichtbar, ohne den Gesamtzustand unnoetig zu dramatisieren.
- Globalisierung ist nur zulaessig, wenn Auth, Workspace oder Kern-API betroffen sind.

### Regel 7: Schlechtester relevante Zustand gewinnt

- Wenn mehrere Evidenzen fuer dieselbe Surface vorliegen, darf die UI nicht besser rendern als die schlechteste relevante aktuelle Evidenz.

## Degradation-Prinzipien

### 1. Sichtbar statt still

- Degradation ist ein sichtbarer Betriebsmodus.
- Versteckte Degradation ist ein Governance-Verstoss.

### 2. Lokal statt total, wenn moeglich

- Search-, Queue-, Retrieval- oder Chat-Probleme bleiben feature-spezifisch, solange Kernpfade intakt sind.
- Nur Kernpfad-Ausfaelle werden global.

### 3. Read-only statt Schein-Erfolg

- Wenn korrekte Mutation oder frische Berechnung nicht belegbar ist, wechselt die Surface auf read-only, stale, degraded oder blocked.

### 4. Unknown statt Fake-Green Quelle: `reports/current/masterplan_status.json`.

- Kann ein degradiertes Signal nicht zuverlaessig verifiziert werden, ist `unknown` der korrekte Zustand.

### 5. Recovery erst nach Verifikation

- Eine degradierte Truth Surface darf erst nach frischer Verifikation wieder auf `ok` oder `fresh` wechseln.

## Verboten

- Fake-Green Quelle: `reports/current/masterplan_status.json`.
- implizite Success-Zustaende
- versteckte Degradation
- optimistic completion ohne Nachweis
- stale Diagnostics ohne Kennzeichnung
- Erfolg aus historischer Evidenz bei aktuellem `unknown`
- Default `active` oder `healthy` bei fehlendem Surface-Nachweis
