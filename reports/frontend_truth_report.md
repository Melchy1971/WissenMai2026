# Frontend Truth Report

| Feld | Wert |
|---|---|
| timestamp | `2026-05-28T07:02:02.534462+00:00` |
| collected | 6 |
| passed | 6 |
| failed | 0 |
| skipped | 0 |
| browser | `chromium` |
| api_base_url | `http://127.0.0.1:8013` |
| test_database_url_set | true |
| duration | 40.49s |
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
