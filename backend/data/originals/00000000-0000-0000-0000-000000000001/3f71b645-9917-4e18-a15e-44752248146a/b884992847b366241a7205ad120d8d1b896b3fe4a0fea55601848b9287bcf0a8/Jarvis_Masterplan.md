# JARVIS Masterplan – Analyse, Zielarchitektur, Implementierungsstatus und Entwicklungs-Prompts

Stand: 2026-06-05  
Basis: `Jarvis.zip` aus aktuellem Chat

---

## 1. Executive Summary

Der aktuelle Stand ist kein produktionsfähiger Assistent, sondern ein funktionsreicher Prototyp mit starker Windows-Desktop-Automatisierung, Live-Audio-Anbindung, PyQt6-UI und vielen Tool-Stubs. Die größte Schwäche ist nicht Syntax oder Struktur, sondern fehlende Produktgrenze: Jarvis verspricht autonome Fähigkeiten, die technisch teils nicht implementiert, teils nur simuliert und teils sicherheitskritisch unkontrolliert sind.

Ziel des Masterplans: Jarvis von einem breiten Demo-/Experimentalsystem zu einem kontrollierten, testbaren, sicheren Windows-Assistenten entwickeln.

---

## 2. Statuslegende

| Status | Bedeutung |
|---|---|
| ✅ Implementiert | Funktion existiert mit erkennbarer Logik und ist grundsätzlich nutzbar. |
| 🟡 Teilweise implementiert | Funktion existiert, aber unvollständig, fragil, nicht sauber abgesichert oder abhängig von lokaler Umgebung. |
| 🔴 Stub / nicht implementiert | Datei oder Tool existiert, liefert aber nur Platzhalter oder Dummy-Antwort. |
| ⚠️ Sicherheitskritisch | Funktion kann System, Dateien, Prozesse, Browser, Eingaben oder Codeausführung beeinflussen. Nur mit Guardrails zulassen. |
| ❌ Entfernen / deaktivieren | Funktion sollte vorerst aus Tool-Registry oder Live-Betrieb entfernt werden. |

---

## 3. Produktziel V1

Jarvis V1 soll kein vollautonomer Agent sein, sondern ein kontrollierter lokaler Windows-Assistent mit folgenden Kernfähigkeiten:

1. Sprach- und Texteingabe über UI.
2. Stabile LLM-Anbindung über Gemini und optional OpenRouter.
3. Sichere Tool-Ausführung über zentrale Registry, Allowlist und Rechtelevel.
4. Lokale Aufgaben: Apps öffnen, Dateien verwalten, einfache Dokumente erzeugen, Wetter/Recherche, Systemstatus.
5. Keine unkontrollierte Selbstmodifikation.
6. Keine simulierten Tool-Erfolge.
7. Vollständiger Smoke-Test für Start, Imports, Config, Tool-Registry und Beispielbefehle.

Nicht-Ziel V1:

- Vollautonome Codeänderung.
- Automatisches Erzeugen neuer Tools im Live-System.
- Echte Gmail/Google Calendar/Drive-Integration ohne OAuth-Konzept.
- Zugriff auf Bank, Käufe, sensible Accounts oder destructive Shell-Kommandos.

---

## 4. Ist-Analyse nach Komponenten

### 4.1 Start, Runtime, Konfiguration

| Komponente | Status | Befund | Konsequenz |
|---|---:|---|---|
| `main.py` | 🟡 | Zentrale Runtime, Live-Session, Tool-Dispatch, UI-Kopplung. Sehr groß und schwer testbar. | Refactoring in App, LLM, ToolRuntime, Config nötig. |
| `ui.py` | 🟡 | PyQt6-Oberfläche vorhanden. Stark an Desktop-Umgebung gekoppelt. | Separat testbar machen, Runtime nicht direkt darin verstecken. |
| `beta_config.py` | 🟡 | Limit-/Pro-Tool-Logik vorhanden. Persistenz einfach. | Für lokale Nutzung ok, aber keine Security-Grenze. |
| `memory/config_manager.py` | 🟡 | API-Key-Handling vorhanden. | Secret-Handling unsicher, echte Keys lagen im Export. |
| `memory/memory_manager.py` | 🟡 | Lokales Langzeitgedächtnis als JSON. | Kein Schema, keine Migration, keine Datenschutzgrenzen. |
| `requirements.txt` | 🟡 | Abhängigkeiten vorhanden. | Windows-/GUI-lastig, keine Lockfile, kein Minimal-Install. |
| `.gitignore` | 🟡 | Enthält Schutzregeln. | Export/Repo dennoch mit `.venv`, `.git`, Logs, Secrets. |

### 4.2 Tools – Implementierungsstatus

| Tool | Status | Risiko | Kurzbewertung |
|---|---:|---:|---|
| `_chrome_launch.py` | 🟡 | ⚠️ | Browserstart vorhanden, aber plattformabhängig. |
| `arca_invoice.py` | 🔴 | niedrig | Nur Stub. |
| `auto_programmer.py` | 🟡 | ⚠️ | Sandbox-Ansatz vorhanden, aber Selbstprogrammierung im Live-System riskant. |
| `browser_control.py` | 🟡 | ⚠️ | pyautogui/Window-Control vorhanden, fragil. |
| `camera_bus.py` | 🟡 | mittel | Signalbus vorhanden. |
| `code_helper.py` | 🟡 | ⚠️ | Codeprüfung/Compile vorhanden, aber Shell-/Pfadgrenzen prüfen. |
| `codebase.py` | 🔴 | niedrig | Stub. |
| `computer_control.py` | 🟡 | ⚠️ | Tastatur/Maus/Clipboard-Automation vorhanden, braucht Rechtelevel. |
| `computer_settings.py` | 🟡 | ⚠️ | Windows-Systemsteuerung vorhanden, stark plattformgebunden. |
| `contextual_control.py` | 🟡 | ⚠️ | Lautstärke/Helligkeit/Power/Focus. Braucht klare Triggergrenzen. |
| `desktop.py` | 🔴 | niedrig | Stub. |
| `document_creator.py` | 🟡 | mittel | DOCX/XLSX-Erzeugung vorhanden. Braucht Pfad-/Formatvalidierung. |
| `document_manager.py` | 🟡 | mittel | Dokumentoperationen vorhanden. Braucht Tests und Pfad-Sandbox. |
| `file_controller.py` | 🟡 | ⚠️ | Umfangreiche Dateioperationen. Destruktive Aktionen absichern. |
| `flight_finder.py` | 🔴 | niedrig | Stub. |
| `gesture_engine.py` | 🟡 | ⚠️ | Kamera/Gestensteuerung vorhanden. Hohe Fragilität und Privacy-Risiko. |
| `git_control.py` | 🔴 | niedrig | Stub. |
| `gmail_control.py` | 🔴 | mittel | Stub, keine echte Gmail-Integration. |
| `goals.py` | 🟡 | niedrig | Einfache JSON-Zielverwaltung. |
| `google_calendar.py` | 🔴 | mittel | Stub. |
| `google_drive.py` | 🔴 | mittel | Stub. |
| `google_maps.py` | 🔴 | niedrig | Stub. |
| `image_generation.py` | 🔴 | niedrig | Stub. |
| `knowledge_base.py` | 🔴 | niedrig | Stub. |
| `morning_brief.py` | 🔴 | niedrig | Fast leer, kein echter Briefing-Prozess. |
| `native_ui.py` | 🟡 | ⚠️ | Fenstersteuerung vorhanden, fragil. |
| `open_app.py` | 🟡 | ⚠️ | App-Start vorhanden. Braucht Allowlist. |
| `openrouter_agent.py` | 🟡 | mittel | OpenRouter-Aufruf vorhanden. Braucht Fehler-/Timeout-/Rate-Limit-Konzept. |
| `proactive_automation.py` | 🟡 | mittel | Automationslogik angedeutet. Unklare Trigger-/Persistenzgrenzen. |
| `reminder.py` | 🟡 | niedrig | Einfache Thread-Erinnerungen. Nicht robust gegen Neustart. |
| `rules_engine.py` | 🟡 | mittel | Regel-/Phrase-Trigger vorhanden. Muss validiert und persistiert werden. |
| `scheduler.py` | 🔴 | niedrig | Stub. |
| `screen_vision.py` | 🟡 | ⚠️ | Screenshot + Vision-LLM vorhanden. Privacy-/Kosten-/Timeout-Risiko. |
| `self_edit.py` | 🟡 | ⚠️ | Selbständerung mit Backup vorhanden. In V1 deaktivieren. |
| `smart_file_organizer.py` | 🟡 | ⚠️ | Datei-Orga/Dedupe vorhanden. Vor Live-Nutzung Dry-Run erzwingen. |
| `smart_home.py` | 🔴 | niedrig | Stub. |
| `social_media.py` | 🔴 | niedrig | Stub. |
| `spotify_control.py` | 🟡 | mittel | Spotify-Steuerung vorhanden. Benötigt Auth-/Fallback-Handling. |
| `system_monitor.py` | ✅ | mittel | Systeminfos/Monitoring weitgehend implementiert. |
| `terminal_agent.py` | 🟡 | ⚠️ | Shell-Ausführung vorhanden. Für V1 stark einschränken oder deaktivieren. |
| `tiktok_analyzer.py` | 🔴 | niedrig | Stub. |
| `tool_creator.py` | 🟡 | ⚠️ | Tool-Erzeugung vorhanden. Für V1 deaktivieren. |
| `unified_communications.py` | 🟡 | mittel | Öffnet Web-Kommunikation, teilweise fragil/simulativ. |
| `user_profile.py` | 🟡 | niedrig | JSON-Profil vorhanden. Schema fehlt. |
| `vision_guardian.py` | 🟡 | ⚠️ | Hintergrund-Screenanalyse. Privacy/Kosten/Fehlalarme. |
| `visual_click.py` | 🟡 | ⚠️ | Screenshot + Klickaktion. Sehr riskant ohne Confirm-Gate. |
| `weather_report.py` | 🟡 | niedrig | Wetter-API-Logik vorhanden. |
| `web_navigation.py` | 🟡 | mittel | Einfache URL-/Webnavigation. Kein vollwertiger Browser-Agent. |
| `web_search.py` | 🔴 | niedrig | Stub. |
| `whatsapp.py` | 🟡 | ⚠️ | WhatsApp-Web-Automation via UI. Fragil, Risiko falscher Empfänger. |
| `windows_settings.py` | 🔴 | niedrig | Stub. |
| `youtube_video.py` | 🟡 | niedrig | YouTube-Suche/Öffnen vorhanden. |

---

## 5. Hauptprobleme

### 5.1 Fehlende Wahrheit im Tool-System

Ist-Zustand:

- LLM erhält Tool-Beschreibungen.
- Einige Tools sind echt.
- Einige Tools sind Stubs.
- Einige Tools wirken erfolgreich, obwohl nichts real passiert.

Fehlerwirkung:

- Nutzer vertraut falschen Ergebnissen.
- Debugging wird unmöglich.
- Agent kann falsche Systemzustände behaupten.

Zielzustand:

Jedes Tool muss eine strukturierte Antwort liefern:

```json
{
  "ok": true,
  "status": "implemented | not_implemented | denied | failed | needs_confirmation",
  "action": "...",
  "result": {},
  "error": null,
  "risk_level": "low | medium | high | critical"
}
```

### 5.2 Sicherheitsmodell fehlt

Ist-Zustand:

- Dateioperationen, Shell, Maus, Tastatur, Browser, Codeänderung und Screenanalyse existieren nebeneinander.
- Es gibt keine zentrale Policy-Schicht.

Zielzustand:

Rechtelevel:

| Level | Bedeutung | Beispiele |
|---|---|---|
| L0 Read-only | Nur lesen/anzeigen | Wetter, Systemstatus, Datei-Liste |
| L1 Safe action | Reversible Aktion | App öffnen, URL öffnen |
| L2 User-confirmed | Bestätigung nötig | Datei verschieben, Nachricht vorbereiten |
| L3 Restricted | Standardmäßig deaktiviert | Shell, Self-Edit, Tool-Creation |
| L4 Forbidden V1 | Nicht erlaubt | Löschen ohne Papierkorb, Credentials lesen, autonome Käufe |

### 5.3 Projektpaket ist nicht sauber

Ist-Zustand:

- `.venv`, `.git`, `__pycache__`, Logs und echte Configs im Export.

Zielzustand:

- Repo enthält nur Source, Beispiele, Docs, Tests.
- Runtime-Daten liegen außerhalb oder in `.local/`.
- Secrets nur über `.env` oder lokale Config, niemals im Export.

---

## 6. Zielarchitektur

```text
jarvis/
  app/
    main.py                 # Startpunkt
    bootstrap.py            # Config, Logging, Dependency Check
    runtime.py              # App Runtime
  config/
    settings.example.json
    tools.yaml              # Tool-Metadaten, Rechtelevel, Aktivierung
  core/
    llm_client.py           # Gemini/OpenRouter Adapter
    tool_runtime.py         # Tool-Dispatch, Policy, Validation
    policy.py               # Rechtelevel, Confirm-Gates
    schemas.py              # Gemeinsame Response-Modelle
    errors.py
  tools/
    system/
    files/
    browser/
    documents/
    communication/
    experimental/
  ui/
    main_window.py
    widgets/
  memory/
    profile_store.py
    conversation_store.py
  tests/
    test_imports.py
    test_config.py
    test_tool_registry.py
    test_tool_contracts.py
  docs/
    MASTERPLAN.md
    SECURITY.md
    TOOLS.md
    SETUP.md
```

---

## 7. Umsetzungsphasen

## Phase 0 – Sofortmaßnahmen: Secrets, Export, Repo-Hygiene

Ziel: Projekt sicher und reproduzierbar machen.

Status: ❌ offen

Aufgaben:

- [ ] API-Keys in `config/api_keys.json` sofort rotieren.
- [ ] `config/api_keys.json` aus Repo/Export entfernen.
- [ ] `config/api_keys.example.json` behalten.
- [ ] `.venv/`, `.git/`, `__pycache__/`, `jarvis.log`, Runtime-State aus Export entfernen.
- [ ] `.gitignore` erweitern und prüfen.
- [ ] `scripts/create_clean_package.py` erstellen.

Akzeptanzkriterien:

- ZIP enthält keine Secrets.
- ZIP enthält keine `.venv` und kein `.git`.
- Clean-Package-Script erzeugt reproduzierbares Artefakt.

## Phase 1 – Tool-Registry und Tool-Wahrheit

Ziel: Kein Tool darf Erfolg simulieren.

Status: ❌ offen

Aufgaben:

- [ ] Zentrale Tool-Registry einführen.
- [ ] Tool-Metadaten definieren: Name, Kategorie, Status, Risiko, Plattform, benötigt Config.
- [ ] Einheitliches Tool-Result-Schema einführen.
- [ ] Alle Stub-Tools auf `not_implemented` setzen.
- [ ] Tool-Dispatch in `main.py` auf Registry umstellen.
- [ ] Null-Import-Fehler abfangen.

Akzeptanzkriterien:

- Jeder Tool-Aufruf liefert strukturiertes Ergebnis.
- Stub-Tools behaupten keinen Erfolg.
- Fehlende Module crashen nicht.

## Phase 2 – Security-Policy und Confirm-Gates

Ziel: Riskante Funktionen kontrollieren.

Status: ❌ offen

Aufgaben:

- [ ] `core/policy.py` erstellen.
- [ ] Rechtelevel L0–L4 implementieren.
- [ ] Confirm-Gate für Dateiänderungen, Nachrichten, Klicks, Shell, Self-Edit.
- [ ] Standardmäßig deaktivieren: `terminal_agent`, `self_edit`, `tool_creator`, `auto_programmer`, `visual_click`.
- [ ] Dry-Run-Modus für Dateioperationen.
- [ ] Pfad-Sandbox definieren: erlaubte Arbeitsverzeichnisse.

Akzeptanzkriterien:

- High-Risk-Tools laufen nicht ohne explizite Freigabe.
- Destruktive Dateiaktionen landen im Papierkorb oder Dry-Run.
- Shell-Kommandos sind allowlist-basiert oder deaktiviert.

## Phase 3 – Stabiler Start und Smoke-Tests

Ziel: Jarvis startet reproduzierbar.

Status: ❌ offen

Aufgaben:

- [ ] `tests/test_imports.py` erstellen.
- [ ] `tests/test_config.py` erstellen.
- [ ] `tests/test_tool_registry.py` erstellen.
- [ ] `tests/test_tool_contracts.py` erstellen.
- [ ] `scripts/smoke_test.py` erstellen.
- [ ] Logging standardisieren.
- [ ] Modellname konfigurierbar machen, kein hartes Preview-Modell.

Akzeptanzkriterien:

- `python -m pytest` läuft.
- Smoke-Test prüft Config, Imports, Tool-Registry, Beispiel-Tool-Aufruf.
- Startfehler zeigen klare Fehlermeldung.

## Phase 4 – V1-Toolset fertigstellen

Ziel: Kleine, echte, robuste Kernfunktionen.

Status: 🟡 teilweise

V1 aktivieren:

- [ ] `system_monitor`
- [ ] `weather_report`
- [ ] `open_app` mit Allowlist
- [ ] `youtube_video`
- [ ] `document_creator`
- [ ] `file_controller` nur mit Sandbox + Dry-Run/Confirm
- [ ] `web_navigation`
- [ ] `reminder` mit persistenter Speicherung
- [ ] `goals`
- [ ] `user_profile`

V1 deaktivieren:

- [ ] `terminal_agent`
- [ ] `self_edit`
- [ ] `tool_creator`
- [ ] `auto_programmer`
- [ ] `visual_click`
- [ ] `vision_guardian`
- [ ] `gesture_engine`

Akzeptanzkriterien:

- 10 Kernbefehle laufen reproduzierbar.
- Keine Stubs in aktivem Toolset.
- Jedes Tool hat Tests für Erfolg, Fehler, ungültige Parameter.

## Phase 5 – Echte Integrationen

Ziel: Google, Gmail, Calendar, Drive, Spotify sauber anbinden.

Status: ❌ offen / teils experimentell

Aufgaben:

- [ ] OAuth-Konzept definieren.
- [ ] Token-Speicher lokal verschlüsseln oder bewusst lokal dokumentieren.
- [ ] Gmail nur Draft/Read in V1, kein automatisches Senden ohne Bestätigung.
- [ ] Calendar nur Lesen + Draft-Termin, kein direktes Einladen ohne Bestätigung.
- [ ] Drive nur Lesen/Upload mit Bestätigung.
- [ ] Spotify Auth prüfen und Fehler sauber melden.

Akzeptanzkriterien:

- Keine Integration gibt Dummy-Erfolg zurück.
- Jeder Schreibzugriff erfordert Bestätigung.
- Tokens werden nicht exportiert.

## Phase 6 – Proaktive Automatisierung

Ziel: Jarvis darf vorschlagen, aber nicht unkontrolliert handeln.

Status: 🟡 experimentell

Aufgaben:

- [ ] Rules Engine mit Schema versehen.
- [ ] Proaktive Vorschläge von Aktionen trennen.
- [ ] Automationen persistieren.
- [ ] Neustartfestigkeit herstellen.
- [ ] Audit-Log pro Automation.

Akzeptanzkriterien:

- Automationen überstehen Neustart.
- Jede Automation hat Owner, Trigger, Aktion, Risiko, letzte Ausführung.
- Riskante Aktionen bleiben confirm-pflichtig.

## Phase 7 – UI/UX-Härtung

Ziel: UI zeigt echte Zustände, nicht Agenten-Fiktion.

Status: 🟡 teilweise

Aufgaben:

- [ ] Tool-Ausführung sichtbar machen: läuft, fertig, fehlgeschlagen, blockiert.
- [ ] Confirm-Dialoge für riskante Aktionen.
- [ ] Konfigurationsscreen für API-Keys, Modell, aktivierte Tools.
- [ ] Fehlerpanel mit kopierbarer Diagnose.
- [ ] Safe Mode Button.

Akzeptanzkriterien:

- Nutzer erkennt, ob Jarvis wirklich gehandelt hat.
- Riskante Aktion wird vor Ausführung angezeigt.
- Safe Mode deaktiviert alle L2+ Tools.

---

## 8. Qualitäts-Gates

| Gate | Mindestanforderung | Go/No-Go |
|---|---|---|
| G0 Clean Repo | Keine Secrets, keine `.venv`, keine Logs | No-Go bei Verstoß |
| G1 Startfähigkeit | App startet mit Beispielconfig oder sauberer Fehlermeldung | No-Go bei Crash |
| G2 Tool-Truth | Keine aktiven Stubs | No-Go bei Dummy-Erfolg |
| G3 Security | Riskante Tools blockiert/confirm-pflichtig | No-Go bei freier Shell/Self-Edit |
| G4 Tests | Import-, Config-, Registry-, Contract-Tests grün | No-Go bei fehlender Testbasis |
| G5 V1 Demo | 10 Kernbefehle funktionieren reproduzierbar | Go für V1 |

---

## 9. Direkte Entwicklungs-Prompts

### Prompt 1 – Clean Repo und Secret-Schutz

```text
Du arbeitest im Projekt Jarvis. Ziel: Repo-Hygiene und Secret-Schutz herstellen.

Aufgaben:
1. Entferne aus dem Projekt alle Runtime-Artefakte: .venv, __pycache__, jarvis.log, lokale State-Dateien und echte api_keys.json.
2. Erweitere .gitignore so, dass Secrets, Logs, virtuelle Umgebungen, PyCache, lokale Modelle und Runtime-State nie versioniert werden.
3. Erstelle config/api_keys.example.json mit Dummywerten.
4. Erstelle scripts/create_clean_package.py. Das Script soll eine saubere ZIP erzeugen und .git, .venv, __pycache__, Logs, Secrets und lokale State-Dateien ausschließen.
5. Erstelle docs/SECURITY.md mit Regeln für Secrets, API-Key-Rotation und Export.

Akzeptanz:
- Clean-ZIP enthält keine echten Keys.
- Clean-ZIP enthält keine .venv, .git, __pycache__ oder Logs.
- Script läuft unter Windows mit Python 3.12.
- Keine funktionale Änderung an Jarvis-Runtime.
```

### Prompt 2 – Tool-Result-Schema

```text
Du arbeitest im Projekt Jarvis. Ziel: Einheitliches Tool-Ergebnis einführen.

Aufgaben:
1. Erstelle core/schemas.py mit ToolResult-Datenstruktur.
2. Felder: ok, status, tool, action, result, error, risk_level, requires_confirmation.
3. Erstelle Helper-Funktionen: success(), failed(), denied(), not_implemented(), needs_confirmation().
4. Passe mindestens diese Tools auf das Schema an: weather_report, system_monitor, open_app, google_calendar, web_search.
5. Stub-Tools dürfen keinen Erfolg mehr behaupten. Sie müssen not_implemented liefern.

Akzeptanz:
- Jeder angepasste Tool-Aufruf liefert ein dict im ToolResult-Format.
- google_calendar und web_search liefern not_implemented statt Dummy-Erfolg.
- Bestehende Aufrufe crashen nicht.
```

### Prompt 3 – Zentrale Tool-Registry

```text
Du arbeitest im Projekt Jarvis. Ziel: Zentrale Tool-Registry einführen.

Aufgaben:
1. Erstelle core/tool_registry.py.
2. Definiere pro Tool: name, module, callable, category, implemented, enabled, risk_level, requires_confirmation, platform.
3. Lade nur aktivierte und implementierte Tools in die LLM-Tool-Declaration.
4. Ändere main.py so, dass Tool-Ausführung über die Registry läuft.
5. Wenn ein Tool fehlt oder Import fehlschlägt, liefere ToolResult failed oder not_implemented, aber keinen Crash.

Akzeptanz:
- Aktive Toolliste kann per Funktion ausgegeben werden.
- Stub-Tools sind nicht aktiv.
- Fehlender Import führt zu kontrollierter Fehlermeldung.
- main.py enthält weniger harte Tool-Sonderfälle.
```

### Prompt 4 – Security Policy und Rechtelevel

```text
Du arbeitest im Projekt Jarvis. Ziel: Sicherheitsmodell für Tool-Ausführung.

Aufgaben:
1. Erstelle core/policy.py.
2. Implementiere Rechtelevel L0_READ, L1_SAFE, L2_CONFIRM, L3_RESTRICTED, L4_FORBIDDEN.
3. Ordne Tools initial zu:
   - L0: system_monitor, weather_report
   - L1: youtube_video, web_navigation, open_app mit Allowlist
   - L2: file_controller, document_creator, whatsapp, visual_click
   - L3: terminal_agent, self_edit, tool_creator, auto_programmer
   - L4: direkte Löschung ohne Papierkorb, beliebige Shell-Kommandos
4. ToolRuntime muss Policy prüfen, bevor ein Tool ausgeführt wird.
5. Restricted Tools sind standardmäßig deaktiviert.

Akzeptanz:
- terminal_agent, self_edit, tool_creator und auto_programmer laufen nicht im Standardmodus.
- L2-Tools liefern needs_confirmation, wenn keine Bestätigung vorliegt.
- L0/L1-Tools laufen weiterhin.
```

### Prompt 5 – Smoke-Test und Pytest-Basis

```text
Du arbeitest im Projekt Jarvis. Ziel: minimale Testbasis schaffen.

Aufgaben:
1. Füge pytest als Dev-Abhängigkeit hinzu.
2. Erstelle tests/test_imports.py und prüfe Import der Kernmodule ohne App-Start.
3. Erstelle tests/test_config.py und prüfe Verhalten mit fehlender api_keys.json.
4. Erstelle tests/test_tool_registry.py und prüfe, dass keine Stub-Tools aktiv sind.
5. Erstelle tests/test_tool_contracts.py und prüfe ToolResult-Schema bei mindestens fünf Tools.
6. Erstelle scripts/smoke_test.py für manuellen Check.

Akzeptanz:
- python -m pytest läuft ohne echte API-Keys.
- Smoke-Test benötigt keine Gemini-Verbindung.
- Fehler sind eindeutig lesbar.
```

### Prompt 6 – main.py entflechten

```text
Du arbeitest im Projekt Jarvis. Ziel: main.py reduzieren und Runtime entkoppeln.

Aufgaben:
1. Extrahiere Config-Laden nach core/config.py.
2. Extrahiere LLM/Gemini-Verbindung nach core/llm_client.py.
3. Extrahiere Tool-Ausführung nach core/tool_runtime.py.
4. main.py soll nur Bootstrap, UI-Start und Runtime-Verknüpfung enthalten.
5. Bestehendes Verhalten darf nicht absichtlich geändert werden.

Akzeptanz:
- main.py wird deutlich kleiner.
- Tool-Dispatch liegt nicht mehr direkt in main.py.
- App startet weiterhin.
- Import-Tests bleiben grün.
```

### Prompt 7 – File Controller absichern

```text
Du arbeitest im Projekt Jarvis. Ziel: Dateioperationen sicher machen.

Aufgaben:
1. Definiere erlaubte Arbeitsbereiche in config/settings.example.json.
2. file_controller darf nur innerhalb erlaubter Pfade arbeiten.
3. Löschoperationen müssen send2trash nutzen, kein permanentes Delete.
4. Füge dry_run=True als Standard für move/copy/delete/organize hinzu.
5. Rückgabe muss geplante Aktion, Zielpfad und Risiko enthalten.

Akzeptanz:
- Pfad außerhalb Sandbox wird denied.
- Delete ist nie permanent.
- Ohne Bestätigung keine Änderung an Dateien.
```

### Prompt 8 – Open App mit Allowlist

```text
Du arbeitest im Projekt Jarvis. Ziel: App-Start absichern.

Aufgaben:
1. Erstelle config/app_allowlist.json mit erlaubten Apps und Pfaden.
2. open_app darf nur bekannte Apps aus dieser Allowlist starten.
3. Freie Pfade oder beliebige exe-Dateien sind standardmäßig verboten.
4. Rückgabe muss enthalten: requested_app, resolved_path, started, error.
5. Füge Tests für erlaubte, unbekannte und fehlende App hinzu.

Akzeptanz:
- Bekannte App startet.
- Unbekannte App wird denied.
- Kein beliebiger Pfadstart ohne explizite Allowlist.
```

### Prompt 9 – Stub-Tools bereinigen

```text
Du arbeitest im Projekt Jarvis. Ziel: Stub-Tools sauber markieren oder entfernen.

Aufgaben:
1. Identifiziere alle Tools mit Platzhalterlogik.
2. Markiere sie in der Tool-Registry als implemented=false und enabled=false.
3. Passe die Funktionen so an, dass sie ToolResult.not_implemented liefern.
4. Entferne ihre Tool-Declarations aus der aktiven LLM-Konfiguration.
5. Dokumentiere sie in docs/TOOLS.md unter Backlog.

Betroffene Tools mindestens:
arca_invoice, codebase, desktop, flight_finder, git_control, gmail_control, google_calendar, google_drive, google_maps, image_generation, knowledge_base, morning_brief, scheduler, smart_home, social_media, tiktok_analyzer, web_search, windows_settings.

Akzeptanz:
- Kein aktiver Stub erzeugt Erfolgsmeldung.
- Backlog enthält alle deaktivierten Tools.
```

### Prompt 10 – V1-Demo-Befehle definieren

```text
Du arbeitest im Projekt Jarvis. Ziel: V1-Demo-Befehle stabilisieren.

Aufgaben:
1. Erstelle docs/V1_DEMO.md.
2. Definiere 10 reproduzierbare Befehle mit erwarteter Tool-Ausführung.
3. Baue optional scripts/run_demo_checks.py, das nicht-interaktive Teile prüft.
4. Markiere Befehle nach Risiko L0-L2.
5. Stelle sicher, dass keine Demo-Funktion einen Stub nutzt.

Vorgeschlagene Befehle:
- Zeige Systemstatus.
- Wie ist das Wetter in Heilbronn?
- Öffne Notepad.
- Öffne YouTube-Suche nach Tischtennis Training Rückschlag.
- Erstelle ein DOCX mit einer kurzen Notiz.
- Liste Dateien im Jarvis-Arbeitsordner.
- Erstelle eine Erinnerung in 10 Minuten.
- Speichere ein Ziel im Profil.
- Öffne eine Website.
- Zeige aktive Toolliste.

Akzeptanz:
- Jeder Demo-Befehl hat erwartetes Ergebnis.
- Jeder Demo-Befehl ist testbar oder manuell prüfbar.
- Keine Dummy-Erfolge.
```

---

## 10. Empfohlene Reihenfolge

1. Prompt 1 – Clean Repo und Secret-Schutz.
2. Prompt 2 – Tool-Result-Schema.
3. Prompt 9 – Stub-Tools bereinigen.
4. Prompt 3 – Zentrale Tool-Registry.
5. Prompt 4 – Security Policy.
6. Prompt 5 – Smoke-Test und Pytest-Basis.
7. Prompt 7 – File Controller absichern.
8. Prompt 8 – Open App Allowlist.
9. Prompt 6 – main.py entflechten.
10. Prompt 10 – V1-Demo-Befehle.

---

## 11. Harte No-Go-Liste bis Abschluss Phase 2

- Keine echte Shell-Ausführung über Jarvis.
- Keine Selbständerung von Code.
- Kein automatisches Erzeugen neuer Tools.
- Kein automatisches Klicken auf UI-Elemente ohne Bestätigung.
- Kein WhatsApp-/Mail-Versand ohne Vorschau und Bestätigung.
- Kein Löschen von Dateien ohne Papierkorb und Bestätigung.
- Keine API-Keys in ZIP, Git oder Logdateien.

---

## 12. Zielmetriken

| Metrik | Zielwert V1 |
|---|---:|
| Aktive Stub-Tools | 0 |
| Import-Test Erfolg | 100 % Kernmodule |
| ToolResult-Konformität | 100 % aktive Tools |
| High-Risk-Tools aktiv im Default | 0 |
| Secrets im Export | 0 |
| V1-Demo-Befehle stabil | 10/10 |
| Permanente Datei-Löschoperationen | 0 |

---

## 13. Entscheidung

Nicht weiter Features hinzufügen. Erst Fundament stabilisieren.

Nächster sinnvoller Entwicklungsschritt: **Prompt 1 ausführen**, danach **Prompt 2 und Prompt 9**. Erst wenn Tool-Wahrheit und Sicherheitsmodell stehen, lohnt sich weiterer Ausbau.
