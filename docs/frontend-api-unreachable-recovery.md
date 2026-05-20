# API_UNREACHABLE Recovery UX

Stand: 2026-05-20

## Ziel

Der Fehlerzustand `API_UNREACHABLE` wird korrekt angezeigt. Dieses Dokument definiert das verbindliche Recovery-Verhalten, damit daraus kein Retry-Storm, kein Spinner-Loop und keine State-Corruption entsteht.

Maschinenlesbare Quelle: `docs/frontend-api-unreachable-recovery.json`.

## Recovery-Regeln

| ID | Bereich | Regel |
|---|---|---|
| AUR-001 | Retry Verhalten | Retry nur fuer `API_UNREACHABLE` und `TIMEOUT`; kein Retry fuer `AUTH_REQUIRED`, `FORBIDDEN`, `WORKSPACE_NOT_CONFIGURED`, `VALIDATION_ERROR`. |
| AUR-002 | Reconnect Interval | Auto-Reconnect mit Backoff `2s`, `5s`, `10s`, `20s`, danach maximal `30s`; hoechstens 5 automatische Versuche pro Ausfallfenster. |
| AUR-003 | Manual Retry | Manueller Retry ist sichtbar, nutzergetriggert, waehrend laufendem Retry deaktiviert und setzt den Backoff-Timer zurueck. |
| AUR-004 | Stale Session Handling | Gespeicherter Token gilt nach Connectivity-Recovery erst nach erfolgreichem `/api/v1/auth/me` wieder als validiert. |
| AUR-005 | Reconnect waehrend Login | Login-Netzwerkfehler schreibt keinen Token, keinen User und keinen Workspace. Retry des Login erfolgt nur nach Nutzeraktion. |
| AUR-006 | Reconnect waehrend Workspace Bootstrap | Token darf als unvalidiert erhalten bleiben; `active_workspace_id` wird erst nach erfolgreichem `/auth/me` vertraut. |
| AUR-007 | Kein Retry Storm | Maximal ein Reconnect pro Browser-Tab in flight; Timer und manuelle Retries duerfen keine parallelen Bootstrap-Requests erzeugen. |
| AUR-008 | Kein Spinner Loop | Jeder Loading-State braucht terminalen Pfad: Erfolg, retrybarer Fehler, nicht retrybarer Fehler oder Timeout. |
| AUR-009 | Keine State Corruption | Spaete Antworten alter Retry-Generationen duerfen Auth-, Workspace- oder Routendaten nicht ueberschreiben. |

## Retry-Strategie

Retrybar:

- `API_UNREACHABLE`
- `TIMEOUT`

Bedingt retrybar:

- `CORS_ERROR`, nur wenn als lokale transiente Konfiguration/Connectivity sichtbar gemacht und nicht als permanenter Auth-/Policy-Fehler bewertet.

Nicht retrybar:

- `AUTH_REQUIRED`
- `FORBIDDEN`
- `WORKSPACE_NOT_CONFIGURED`
- `VALIDATION_ERROR`
- `AUTH_INVALID_CREDENTIALS`
- `WORKSPACE_ACCESS_FORBIDDEN`

Auto-Reconnect:

| Feld | Wert |
|---|---|
| Aktiv nach validierter Session | ja |
| Aktiv waehrend initialem Login | nein |
| Aktiv waehrend initialem Bootstrap | nein |
| Intervalle | `2s`, `5s`, `10s`, `20s`, `30s` |
| Max. Versuche | 5 |
| Jitter | 20% |
| Max. In-Flight | 1 |

Manual Retry:

- erlaubt fuer Login-, Auth-Bootstrap-, Workspace-Bootstrap- und Route-Load-Connectivity-Fehler
- deaktiviert, solange ein Retry laeuft
- setzt Backoff zurueck
- braucht sichtbaren Fehlerzustand

## Runtime-Recovery-State-Machine

```text
unauthenticated
  -- login_submit --> authenticating
  -- manual_retry_without_token --> unauthenticated

authenticating
  -- login_success --> workspace_loading
  -- login_network_failure --> api_unreachable
  -- 401 --> unauthenticated
  -- 403 --> forbidden

workspace_loading
  -- auth_me_success_with_workspace --> workspace_ready
  -- auth_me_network_failure --> api_unreachable
  -- no_membership_or_workspace_invalid --> forbidden

workspace_ready
  -- route_request_network_failure --> reconnecting

reconnecting
  -- reconnect_success_auth_workspace_valid --> workspace_ready
  -- max_attempts_exhausted --> api_unreachable
  -- retry_401 --> unauthenticated
  -- retry_403 --> forbidden

api_unreachable
  -- manual_retry_with_token --> authenticating
  -- manual_retry_without_token --> unauthenticated
```

Verboten:

- `api_unreachable -> workspace_ready` ohne erfolgreichen Auth-/Workspace-Refresh
- `authenticating -> workspace_ready` ohne Workspace-Validierung
- `reconnecting -> workspace_ready` ohne Cache-Refresh
- `api_unreachable -> empty_state`

## Implementierungsstand

| Punkt | Stand |
|---|---|
| Manual Retry fuer Bootstrap | vorhanden |
| Auto-Reconnect mit Begrenzung | nicht verifiziert |
| Request-Generation-Guard gegen spaete Responses | nicht verifiziert |
| Stale read-only Routenmodus | teilweise dokumentiert |
| Truth-Status | definiert, noch nicht voll truth-validiert |

## Gate-Auswirkung

Diese Regeln sind M3a-/Frontend-Truth-relevant. Solange Auto-Reconnect, Generation-Guard und stale read-only Routenmodus nicht truth-validiert sind, darf `API_UNREACHABLE` Recovery nur als definiert/teilweise implementiert, nicht als vollstaendig gate-passed behauptet werden.
