# Frontend Accessibility & Operational Clarity Standards

Stand: 2026-05-18

Ziel: Kritische Systemzustaende muessen fuer alle Nutzer eindeutig erkennbar sein. Accessibility und operative Klarheit sind keine kosmetischen Themen, sondern Teil der Governance fuer Error States, degraded states, Recovery, Truth Surfaces und sicherheitsrelevante Aktionen.

Verbindliche Bezugsdokumente:

- `docs/frontend-error-state-catalog.md`
- `docs/frontend-recovery-ux-model.md`
- `docs/frontend-strategic-principles.md`
- `docs/frontend-truth-surface-model.md`
- `docs/frontend-offline-degraded-strategy.md`
- `docs/frontend-runtime-state-machine.md`
- `docs/operational-truth-governance.md`

## Accessibility Standards

### 1. Error States klar

- Jeder Error State braucht einen klaren Titel, eine klare Ursache und eine klare naechste Aktion.
- Error States duerfen nicht nur ueber Farbe oder Icon kommuniziert werden.
- Technischer Fehlercode oder technische Fehlerklasse muss sichtbar oder assistiv ableitbar bleiben.
- Error States muessen per Keyboard erreichbar und per Screenreader sinnvoll erfassbar sein.

### 2. Degraded States verstaendlich

- `degraded`, `maintenance`, `stale`, `unknown` und `blocked` werden in nutzerverstaendliche Sprache uebersetzt.
- Ein degradierter Zustand braucht immer eine sichtbare Erklaerung, was noch funktioniert und was nicht.
- Degraded-Warnungen duerfen nicht in untergeordneten Bereichen versteckt werden, wenn sie den aktuellen Nutzerfluss betreffen.

### 3. Destructive Actions sichtbar

- Destructive oder schwer reversible Aktionen brauchen sichtbare Kennzeichnung ueber Text, Tonalitaet und Kontext.
- Buttons oder Links fuer Archive, Delete, Restore-nahe oder andere riskante Operationen muessen ihren Zweck klar benennen.
- Bestatigungs- oder Warntexte duerfen nicht generisch sein; sie muessen die konkrete Konsequenz benennen.

### 4. Restore-/Reindex-Zustaende eindeutig

- Restore und Reindex muessen als Maintenance- oder Read-only-Zustand sichtbar werden.
- Nutzer duerfen diese Zustaende nicht mit normalem Laden oder normalem Warten verwechseln.
- Such-, Chat- oder Mutationsflaechen muessen ihren eingeschraenkten Status textlich benennen.

### 5. Queue-/Drift-Warnungen sichtbar

- Queue- und Drift-Warnungen sind operative Signale und duerfen nicht nur in Admin-Randbereichen leben, wenn sie Fachpfade beeinflussen.
- Warnungen brauchen mindestens: Label, Schweregrad, betroffene Funktion und Konsequenz.
- Unbekannte Evidenz ist als `unknown` oder `nicht bestaetigt` sichtbar zu machen.

### 6. Keyboard Navigation

- Alle kritischen Banner, Dialoge, Retry-Buttons, destructive actions und Statuskarten muessen per Keyboard erreichbar sein.
- Fokus darf bei Recovery-, Error- oder Warning-Zustaenden nicht verloren gehen.
- Interaktive Elemente brauchen sichtbaren `focus-visible`-Zustand.
- Keine kritische Aktion darf nur ueber Hover oder Pointer-only-Interaktion erreichbar sein.

### 7. Screenreader-Kompatibilitaet

- Kritische Hinweise brauchen sinnvolle semantische Struktur, z. B. Ueberschrift, Beschreibung und Aktion.
- Wichtige Statuswechsel sollen in geeigneten Live-Regionen oder klaren Landmarken erscheinen, wenn sie den aktuellen Nutzerfluss unmittelbar betreffen.
- `Retry`, `Neu laden`, `Zur Anmeldung`, `Workspace pruefen` und vergleichbare Aktionen muessen sprechende Labels haben.
- Ein Screenreader muss auch ohne Farbe oder Layout-Wechsel erkennen koennen, ob ein Zustand `error`, `warning`, `critical`, `stale` oder `blocked` ist.

## Operational Clarity Regeln

### Regel 1: Keine Status nur ueber Farbe

- Farbe darf Severity verstaerken, aber niemals die einzige Information sein.
- Jeder kritische Zustand braucht zusaetzlich Text, Icon, Badge oder semantische Struktur.

### Regel 2: Keine versteckten kritischen Hinweise

- Kritische Warnungen duerfen nicht hinter Akkordeons, Tabs, Hover-Zustaenden oder nachgelagerten Detailkacheln versteckt werden, wenn der aktuelle Flow betroffen ist.
- Global relevante Stoerungen brauchen globale Sichtbarkeit.
- Feature-relevante Stoerungen brauchen mindestens lokale Sichtbarkeit direkt im betroffenen Bereich.

### Regel 3: Keine unklaren Retry-Buttons

- Ein Retry-Button muss benennen oder erkennbar machen, was erneut versucht wird.
- Retry darf nur erscheinen, wenn der Fehler retrybar ist.
- Retry-Buttons brauchen eine sichtbare Folgeerwartung, z. B. `Erneut versuchen`, `Suche erneut laden`, `Verbindung erneut pruefen`.
- Kein Retry ohne klaren Fehler- oder Recovery-Kontext.

### Regel 4: Schlechtester relevante Zustand gewinnt

- Wenn mehrere Status vorliegen, darf die UI keinen optisch besseren Zustand zeigen als die schlechteste relevante aktuelle Evidenz.
- `warning`, `critical`, `stale`, `unknown` oder `blocked` duerfen nicht durch dekorative Success-Elemente optisch neutralisiert werden.

### Regel 5: Erlaubte und blockierte Aktionen muessen sichtbar getrennt sein

- Bei degraded oder Recovery-Zustaenden muss klar sein, welche Aktionen erlaubt sind und welche blockiert bleiben.
- Disabled-Aktionen brauchen eine erkennbare Begruendung oder einen Kontext-Hinweis.

### Regel 6: Destruktive und blockierte Pfade brauchen Klartext

- `Delete`, `Archivieren`, `Wiederherstellen`, `Upload blockiert`, `Search nicht verfuegbar`, `Chat Retrieval veraltet` und aehnliche Zustande brauchen Klartext statt impliziter UI-Konvention.

## UI-Warnstandards

### Warnstufen

| Stufe | Bedeutung | Pflichtbestandteile |
|---|---|---|
| `info` | beobachtbarer Zustand ohne akute Blockierung | Label, kurze Bedeutung, optional Folgeaktion |
| `warning` | eingeschraenkter oder potentiell riskanter Zustand | Label, Ursache, betroffene Funktion, naechste Aktion |
| `critical` | akute Blockierung, Sicherheits- oder Wahrheitsrisiko | Label, klare Konsequenz, blockierte Aktionen, Recovery-Pfad |
| `unknown` | fehlende oder unbelegte Evidenz | Label, Hinweis auf unbelegte Lage, empfohlene Verifikation |

### Pflichtbestandteile jeder Warnsurface

- sichtbarer Titel oder Kurzlabel
- textliche Beschreibung der Lage
- Severity nicht nur farblich, sondern auch textlich oder semantisch erkennbar
- betroffene Funktion oder Konsequenz
- naechste Aktion oder Erklaerung, warum keine Aktion verfuegbar ist

### Platzierungsregeln

- globale Stoerungen: Shell-Banner oder prominente Kopfsektion
- feature-spezifische Stoerungen: direkt am betroffenen Panel, Formular oder Ergebnisbereich
- destructive warnings: direkt am ausloesenden Kontrollpunkt und in der Bestatigung

### Verboten

- kritische Warnungen nur als Badge ohne Text
- Retry-Button ohne Bezug zur betroffenen Operation
- nur farblicher Unterschied zwischen `ok`, `warning` und `critical`
- wichtige Warnungen ausserhalb des sichtbaren Bereichs ohne Fokus- oder Scroll-Strategie
- Warnhinweise, die nur in Tooltips oder Hover-Zustaenden existieren

## Prueffragen

### Accessibility

- Ist jeder kritische Zustand auch ohne Farbe verstaendlich?
- Sind Warnungen, Fehler und blockierte Aktionen per Keyboard erreichbar?
- Sind wesentliche Hinweise fuer Screenreader semantisch nachvollziehbar?

### Operative Klarheit

- Ist klar, was kaputt ist, was noch funktioniert und was der Nutzer als Naechstes tun kann?
- Ist Retry nur dort sichtbar, wo Retry wirklich sinnvoll ist?
- Sind Restore, Reindex, Drift, Queue und Recovery von Normalbetrieb eindeutig unterscheidbar?

## No-Go-Patterns

- Status nur ueber Gruen/Gelb/Rot ohne Text vermitteln
- kritische Hinweise in dekorativen Kacheln ohne Prioritaet verstecken
- unklare Buttons wie `Erneut`, `Weiter`, `OK` ohne konkreten Recovery-Bezug
- destructive actions ohne sichtbare Konsequenz oder Warntext
- Screenreader-relevante Hinweise nur visuell rendern
- Fokusverlust nach Banner-, Dialog- oder Error-State-Umschaltung