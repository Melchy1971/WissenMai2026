# Rollenmodell v2

**Datum:** 2026-06-12
**MVP:** Benutzer + Administrator
**Spätere Phasen:** Reviewer, Auditor

---

## Rollendefinitionen

### Benutzer (User)

Standardrolle für alle authentifizierten Anwender. Arbeitet mit dem Wissensbestand: sucht, importiert, liest.

### Administrator (Admin)

Erweiterte Rechte für Workspace-Management, Qualitätskontrolle und Systemkonfiguration. Kein technisches Systemwissen erforderlich.

---

## Sichtbare Navigation je Rolle

| Navigationspunkt | Benutzer | Administrator |
|-----------------|---------|--------------|
| Dashboard | ja | ja |
| Dokumente | ja | ja |
| Import | ja | ja |
| Suche | ja | ja |
| Themen | ja | ja |
| Datenanalyse | ja | ja |
| Einstellungen | ja (eingeschränkt) | ja (vollständig) |
| Admin-Bereich | nein | ja |

---

## Rechte je Rolle — Dokumente

| Aktion | Benutzer | Administrator |
|--------|---------|--------------|
| Dokumentliste ansehen | ja | ja |
| Dokumentdetail ansehen | ja | ja |
| Dokument importieren | ja | ja |
| Metadaten bearbeiten (Titel, Tags, Kategorie) | ja (eigene Dokumente) | ja (alle) |
| Dokument archivieren | ja (eigene) | ja (alle) |
| Dokument löschen | nein | ja |
| Versionshistorie ansehen | ja | ja |

---

## Rechte je Rolle — Import

| Aktion | Benutzer | Administrator |
|--------|---------|--------------|
| Datei importieren | ja | ja |
| Importverlauf ansehen (eigene) | ja | ja |
| Importverlauf ansehen (alle) | nein | ja |
| Fehlgeschlagenen Import erneut versuchen | ja (eigene) | ja (alle) |

---

## Rechte je Rolle — Suche

| Aktion | Benutzer | Administrator |
|--------|---------|--------------|
| Suche ausführen | ja | ja |
| Ergebnisse ansehen | ja | ja |
| Suchverlauf ansehen (eigener) | ja | ja |

---

## Rechte je Rolle — Datenanalyse / Chat

| Aktion | Benutzer | Administrator |
|--------|---------|--------------|
| Analyse-Workflow starten | ja | ja |
| Fragen stellen (RAG) | ja | ja |
| Dokument freigeben (Schritt 6) | ja (eigene) | ja (alle) |

---

## Rechte je Rolle — Themen

| Aktion | Benutzer | Administrator |
|--------|---------|--------------|
| Themen ansehen | ja | ja |
| Thema erstellen | ja | ja |
| Thema bearbeiten | ja (eigene) | ja (alle) |
| Thema löschen | nein | ja |
| Dokument zu Thema hinzufügen | ja | ja |

---

## Rechte je Rolle — Einstellungen

| Sektion | Benutzer | Administrator |
|---------|---------|--------------|
| Darstellung (Dark Mode, Sprache) | ja | ja |
| KI-Provider | nein | ja |
| Import & Suche (Chunk-Einstellungen) | nein | ja |
| Benutzer verwalten | nein | ja (Future Phase) |
| Workspace-Einstellungen | nein | ja (Future Phase) |

---

## Admin-Bereich (nur Administratoren)

| Funktion | Beschreibung |
|----------|-------------|
| Qualitätshinweise (Detail) | Alle Qualitätsbefunde mit Details — verständliche Sprache |
| Importverlauf (alle Nutzer) | Vollständige Importhistorie |
| Systemstatus | API erreichbar, DB-Status (kein Gate-Status) |
| Benutzer | Future Phase |
| Workspace | Future Phase |

---

## Spätere Rollen (nicht MVP)

### Reviewer

- Kann Freigabe-Schritt (Analyse-Workflow Schritt 6) für andere durchführen
- Kann keine Konfiguration ändern
- Sieht alle Dokumente im Read-only-Modus

### Auditor

- Nur Lesezugriff auf alle Bereiche
- Sieht Importverlauf und Qualitätshinweise
- Kein Import, kein Bearbeiten, kein Freigeben

---

## Hinweis: Workspace-Isolation

Alle Rechte gelten innerhalb eines Workspace. Ein Benutzer sieht keine Dokumente, Themen oder Importe eines anderen Workspace. Admin-Rechte gelten nur für den eigenen Workspace (kein Super-Admin in MVP).
