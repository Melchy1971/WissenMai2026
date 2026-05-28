# M5 Health Score

Stand: 2026-05-11

## Status

- Phase: Vorbereitung
- Implementierung: nicht gestartet
- Freigabestatus: nicht freigegeben
- Truth-Status: nicht als gruen behauptet, bis ein aktueller PostgreSQL-Truth-Report den entsprechenden M5-Block belegt

Statuslogik:

- Dieses Dokument definiert nur die Spezifikation des M5 Health Score.
- Die formale M5-Implementierungsfreigabe ist erreicht, aber dieser Slice ist damit noch nicht automatisch gestartet.
- Die Existenz einer Formel ist kein Nachweis einer laufenden Berechnung im System.
- Eine Aussage wie `healthy`, `degraded` oder `unhealthy` darf erst als betrieblicher Zustand dokumentiert werden, wenn reale Messgrundlagen und PostgreSQL-Truth-Nachweise vorliegen.

## Zweck

- Beschreibt Formel, Gewichte und Statusklassen des M5 Health Score.
- Trennt Spezifikation klar von spaeterer Implementierung und Freigabe.

## Scope in Vorbereitung

- Score-Formel mit Teilkomponenten
- Gewichtungslogik
- Statusklassen `healthy`, `degraded`, `unhealthy`
- Bezug zu Truth-Tests und Reports

## Vorbereitete Komponenten

- Data Quality – 25 %
- Drift – 20 %
- Queue Health – 15 %
- Search/Retrieval Health – 15 %
- Backup Freshness – 10 %
- Error Rate – 10 %
- Documentation Truth – 5 %

## Statuslogik fuer spaetere Fortschreibung

- `Vorbereitung`: Formel und Bewertungslogik sind dokumentiert.
- `Nachweis vorbereitet`: Report- und Truth-Bezug sind beschrieben.
- `Nachweis gruen`: darf erst dokumentiert werden, wenn ein aktueller PostgreSQL-Truth-Report den M5-Block `health_score` grün belegt.
- `Betrieblicher Score aktiv`: darf erst behauptet werden, wenn reale Berechnung, Reportausgabe und Gate-Logik nachweisbar vorhanden sind.

## Platzhalter fuer Nachweise

- Truth-Test-Block: `health_score`
- geplanter Report-Bezug: `reports/current/m4_truth_report.json`
- geplanter Score-Report: noch nicht implementiert

## Nicht-Scope

- keine produktive Live-Berechnung behaupten
- keine Gate-Freigabe allein aus Dokumentation ableiten
- keine Behauptung eines gestarteten M5-Monitorings
