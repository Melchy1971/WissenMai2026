# Backup und Restore Runbook

Stand: 2026-05-11

## Zweck

Dieses Runbook beschreibt den operativen Zielprozess fuer M4e Backup und Restore im lokalen Produktbetrieb.

Das fachliche Konzept und die Architekturregeln stehen in [docs/m4e-backup-restore.md](H:/WissenMai2026/docs/m4e-backup-restore.md).

## Betriebsziel

- Das System soll nach DB- oder Dateisystemfehlern vollstaendig wiederherstellbar sein.
- Ein Backup gilt nur dann als erfolgreich, wenn Datenbank, technische Originaldatei-Kopien, Konfiguration und Manifest konsistent vorliegen.
- Search-Index-Dateien sind nicht pflichtig, weil der Index rekonstruierbar ist.

## Abgrenzung zu M4d Admin Actions

- Dieses Runbook beschreibt einen operativen M4e-Minimal-Prozess, keinen freigegebenen M4d-Full-Admin-Slice.
- M4d read-only bleibt auf Diagnose-Endpunkte ohne Mutation begrenzt.
- Mutierende Admin-Aktionen wie allgemeiner Reindex, Cleanup, Repair Jobs oder Userverwaltung bleiben durch dieses Runbook weiterhin blockiert.
- Vor M5 sind aus diesem Themenfeld nur die fuer M4e-Minimal notwendigen Betriebsfaehigkeiten zulaessig: Backup erzeugen und Search-Index nach Restore neu aufbauen.
- Diese Betriebsfaehigkeiten sollen vor M5 vorzugsweise ueber CLI und Runbook ausgefuehrt werden, nicht als allgemeine Web-Admin-Funktionen.

## Minimaler manueller Ablauf

1. Applikation in einen ruhigen Betriebszustand bringen.
2. `python -m app.cli backup create --output <path>` ausfuehren.
3. `python -m app.cli backup validate --input <path>` ausfuehren.
4. Manifest und `checksums.json` pruefen.
5. Backup-Artefakt an einen getrennten Speicherort kopieren.

## Minimaler Restore-Ablauf

1. Zielumgebung vorbereiten.
2. Sicherstellen, dass die Ziel-Datenbank leer ist.
3. `python -m app.cli backup validate --input <path>` ausfuehren.
4. `python -m app.cli backup restore --input <path>` ausfuehren.
5. Integritaetspruefung starten.
6. Falls noetig `python -m app.cli search rebuild-index` erneut ausfuehren.

## Operative Pflichtpruefungen

- Sind alle im Manifest deklarierten Dateien vorhanden?
- Stimmen die Hashwerte?
- Ist die Datenbank nach Restore erreichbar?
- Ist die Migration auf `head`?
- Ist der Search-Index neu baubar?

## Status in M4e

- Konzept definiert
- CLI-first Codepfad fuer Backup, Validate, Restore und Reindex vorhanden
- technische Originaldatei-Kopien werden im Importpfad abgelegt
- operative Automatisierung weiterhin nicht implementiert
- praktischer Restore-Endlauf gegen eine leere reale lokale PostgreSQL-Ziel-DB nachgewiesen
