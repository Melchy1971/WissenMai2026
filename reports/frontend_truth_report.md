# Frontend Truth Report

| Feld | Wert |
|---|---|
| timestamp | `2026-05-19T07:54:48.841078+00:00` |
| collected | 82 |
| passed | 82 |
| failed | 0 |
| skipped | 0 |
| browser | `chromium` |
| api_base_url | `http://127.0.0.1:8000` |
| test_database_url_set | true |
| duration | 84.54s |
| playwright_exit_code | 0 |
| real_api | true |
| mock_only | false |
| api_database_health | true |

## Failed Flows

- keine

## Gate-Regeln

- `TEST_DATABASE_URL` muss gesetzt sein.
- `/health/db` der echten API muss erfolgreich sein.
- `collected > 0`, `passed == collected`, `failed == 0`, `skipped == 0`.
- `playwright_exit_code == 0`.
- `mock_only == false` und `real_api == true`.
