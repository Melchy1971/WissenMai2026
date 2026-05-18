# Frontend Truth Report

| Feld | Wert |
|---|---|
| timestamp | `2026-05-18T13:28:04.574930+00:00` |
| collected | 22 |
| passed | 22 |
| failed | 0 |
| skipped | 0 |
| browser | `chromium` |
| api_base_url | `http://127.0.0.1:8000` |
| test_database_url_set | true |
| duration | 17.04s |
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
