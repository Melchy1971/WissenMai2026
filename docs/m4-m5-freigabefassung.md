# M4/M5 Freigabefassung

Stand: 2026-05-07

Zweck: Dieses Dokument enthaelt nur den aktuell freigabefaehigen Wahrheitsstand fuer M4 und M5. Historische Zwischenstaende, ueberholte Scores und Zielbilder ohne aktuellen Nachweis sind bewusst ausgeschlossen.

## Aktueller Entscheidungsstand

- M4 ist aktuell nicht technisch stabilisiert.
- Der aktuelle Hardening-Score fuer M4 liegt bei `74/100`.
- Freigaberegel: `>= 90` waere erforderlich; damit bleibt M4 blockiert.
- M5 bleibt blockiert.
- M5 bleibt auch dann blockiert, wenn M4 spaeter technisch stabilisiert wird, solange die vollstaendige Dokumentationspruefung nicht abgeschlossen ist.

## Aktuell beweisbare Aussagen

- Der technische Backend-Kern fuer M4a Auth und Workspace-Kontext ist vorhanden.
- Upload, Search, Chat und Diagnostics verwenden den aktuellen serverseitig aufgeloesten Request-Kontext.
- M4a ist nicht abgeschlossen.
- M4b ist nicht abgeschlossen.
- M4c ist nicht abgeschlossen.
- M4d ist nur als read-only Diagnostics-Slice vorbereitet.
- `GET /api/v1/admin/diagnostics` ist als read-only Endpunkt real implementiert.
- `GET /api/v1/admin/search-index/inconsistencies` ist als read-only Diagnosequelle real implementiert.
- `POST /api/v1/admin/search-index/rebuild` ist aktuell nicht freigegeben und liefert `501 ADMIN_ACTION_NOT_IMPLEMENTED`.
- Mutierende Admin-Aktionen wie Reindex, Cleanup, Backup, Restore, Repair, User- oder Workspace-Verwaltung sind nicht freigegeben.
- Historische Chat-Citations bleiben fuer archivierte oder geloeschte Dokumente sichtbar.
- Search und neues Chat-Retrieval arbeiten nur auf aktiven Dokumenten.

## Nachweisgrenzen

- Der aktuelle lokale Hardening- und Dokumentationslauf ersetzt keinen echten PostgreSQL-Truth-Nachweis.
- Die PostgreSQL-Truth-Suite ist vorhanden, aber im aktuellen Lauf nicht gruen verifiziert.
- Der letzte echte PostgreSQL-Verifikationsversuch fuer Search/Reindex ist an `ConnectionTimeout` gegen die konfigurierte Ziel-Datenbank gescheitert.
- Search/Chat-Konsistenz ist als Truth-Test vorbereitet, aber aktuell nicht als gruener PostgreSQL-Nachweis belegt.
- Der parallele PostgreSQL-Race-Test fuer Duplicate-Imports ist vorhanden, aber aktuell nicht als gruener Pflichtnachweis erbracht.
- Lifecycle-Mutationen sind auth-geschuetzt, aber nicht hart workspace-scoped bis in den Lifecycle-Service nachgewiesen.

## Freigabeaussagen, die nicht verwendet werden duerfen

- M4 ist abgeschlossen.
- M4 ist technisch stabilisiert.
- M4d ist vollstaendig abgeschlossen.
- Mutierende Admin-Aktionen sind freigegeben.
- Search/Chat-Konsistenz ist aktuell auf echter PostgreSQL-DB gruen bewiesen.
- PostgreSQL-Truth-Tests sind fuer den aktuellen Stand gruen nachgewiesen.
- M5 kann starten.

## Minimale Freigabelogik ab heute

1. M4 bleibt blockiert, solange der Hardening-Score unter `90` liegt.
2. M4 bleibt blockiert, solange der echte PostgreSQL-Truth-Nachweis nicht gruen ist.
3. M4d bleibt auf read-only begrenzt, bis M4a, M4b und M4c gruene Gates haben.
4. M5 bleibt blockiert, bis M4 technisch stabilisiert ist.
5. M5 bleibt zusaetzlich blockiert, bis die vollstaendige Dokumentationspruefung abgeschlossen ist.
