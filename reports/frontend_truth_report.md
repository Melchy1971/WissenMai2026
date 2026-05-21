# Frontend Truth Report

| Feld | Wert |
|---|---|
| timestamp | `2026-05-20T13:38:07.880314+00:00` |
| collected | 100 |
| passed | 5 |
| failed | 37 |
| skipped | 58 |
| browser | `chromium` |
| api_base_url | `http://127.0.0.1:8000` |
| test_database_url_set | true |
| duration | 607.49s |
| playwright_exit_code | 1 |
| real_api | true |
| mock_only | false |
| api_database_health | true |

## Failed Flows

- `01 Login flow > redirects unauthenticated request to login page`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Anmeldung' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Anmeldung' })[22m


  12 |   test('redirects unauthenticated request to login page', async ({ page }) => {
  13 |     await page.goto('/documents');
> 14 |     await expect(page.
- `02 Auth bootstrap â€” 01 no token > redirects to /login without token`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Anmeldung' })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 10000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Anmeldung' })[22m


  21 |   test('redirects to /login without token', async ({ barePage }) => {
  22 |     await barePage.goto('/documents');
> 23 |     await expect(barePage.
- `02 Auth bootstrap â€” 01 no token > no workspace error shown on login page`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Anmeldung' })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 10000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Anmeldung' })[22m


  43 |   test('no workspace error shown on login page', async ({ barePage }) => {
  44 |     await barePage.goto('/documents');
> 45 |     await expect(bare
- `02 Auth bootstrap â€” 02 bootstrap resolves > calls /auth/me exactly once during bootstrap`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  69 |     );
  70 |     await page.goto('/documents');
> 71 |     await expect(page.getByRole('heading', { name: 'Dokumente', exa
- `02 Auth bootstrap â€” 02 bootstrap resolves > bootstrap resolves to documents page`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `02 Auth bootstrap â€” 02 bootstrap resolves > workspace id appears in page header after bootstrap`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `02 Auth bootstrap â€” 02 bootstrap resolves > no error state after successful bootstrap`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `02 Auth bootstrap â€” 03 complete session > no bootstrap loading flash with complete session`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `02 Auth bootstrap â€” 03 complete session > app shell renders without error state`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `02 Auth bootstrap â€” 03 complete session > complete session does not call /auth/me`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 10000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  130 |     );
  131 |     await page.goto('/documents');
> 132 |     await expect(page.getByRole('heading', { name: 'Dokumente', 
- `02 Auth bootstrap â€” 04 invalid token > shows session-expired error, does not redirect silently`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  153 |
  154 |     // Should show auth error (session expired), NOT silently redirect or show blank page
> 155 |     await expect(page.locator('.state-card--error')).toBeVisible({ tim
- `02 Auth bootstrap â€” 04 invalid token > invalid token error contains session-expired messaging`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  169 |     });
  170 |     await page.goto('/documents');
> 171 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                       
- `02 Auth bootstrap â€” 05 backend unreachable > shows API_UNREACHABLE error with retry button`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  200 |
  201 |     await page.goto('/documents');
> 202 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 05 backend unreachable > retry button re-triggers bootstrap`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  232 |
  233 |     await page.goto('/documents');
> 234 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 06 no workspace membership > shows workspace-not-configured error for user with no memberships`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.state-card--error') to be visible[22m


   at fixtures.js:46

  44 |     { timeout: 15_000 },
  45 |   );
> 46 |   await page.waitForSelector('.state-card--error', { state: 'visible', timeout: 15_000 });
     |              ^
  47 | }
  48 |
  49 | export const test = base.extend({
    at waitForProtectedErrorReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:46:14)
    at Object.noMe
- `02 Auth bootstrap â€” 06 no workspace membership > no-membership error is not AUTH_SESSION_EXPIRED`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.state-card--error') to be visible[22m


   at fixtures.js:46

  44 |     { timeout: 15_000 },
  45 |   );
> 46 |   await page.waitForSelector('.state-card--error', { state: 'visible', timeout: 15_000 });
     |              ^
  47 | }
  48 |
  49 | export const test = base.extend({
    at waitForProtectedErrorReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:46:14)
    at Object.noMe
- `02 Auth bootstrap â€” 07 forbidden > shows error state on 403 from /auth/me`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  281 |
  282 |     await page.goto('/documents');
> 283 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 07 forbidden > 403 error does not show retry button`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  308 |
  309 |     await page.goto('/documents');
> 310 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 08 logout > logout clears session and redirects to login`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  332 |   }, authState);
  333 |   await page.goto('/documents');
> 334 |   await expect(page.getByRole('heading', { name: 'Dokume
- `02 Auth bootstrap â€” 08 logout > after logout, navigating to /documents redirects to login`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  332 |   }, authState);
  333 |   await page.goto('/documents');
> 334 |   await expect(page.getByRole('heading', { name: 'Dokume
- `02 Auth bootstrap â€” 08 logout > after logout, localStorage is cleared`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  332 |   }, authState);
  333 |   await page.goto('/documents');
> 334 |   await expect(page.getByRole('heading', { name: 'Dokume
- `02 Auth bootstrap â€” 08 logout > after logout, a fresh login restores workspace ready state`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  332 |   }, authState);
  333 |   await page.goto('/documents');
> 334 |   await expect(page.getByRole('heading', { name: 'Dokume
- `03 Workspace loading > shows active workspace id in documents page header`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `03 Workspace loading > shows active workspace id in app shell session area`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `03 Workspace loading > shows navigation links in shell header`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `03 Workspace loading > shows logout button when authenticated`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `03 Workspace loading > does not show workspace missing warning when workspace is configured`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > shows documents page heading`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > shows empty state for workspace with no documents`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > loads the seeded active document in the list`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > opens document detail with versions and chunk preview`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > unknown document detail is an error state, not an empty list`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > empty document list is distinct from an API error`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > shows lifecycle filter section`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > shows upload section`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `04 Dokumentliste > shows search section`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1
- `05 Upload flow > shows upload form elements`: TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
[2m  - waiting for locator('.shell') to be visible[22m


   at fixtures.js:35

  33 |     { timeout: 15_000 },
  34 |   );
> 35 |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
     |              ^
  36 |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37 | }
  38 |
    at waitForProtectedDocumentsReady (H:\WissenMai2026\frontend\tests\gui_truth\fixtures.js:35:1

## Gate-Regeln

- `TEST_DATABASE_URL` muss gesetzt sein.
- `/health/db` der echten API muss erfolgreich sein.
- `collected > 0`, `passed == collected`, `failed == 0`, `skipped == 0`.
- `playwright_exit_code == 0`.
- `mock_only == false` und `real_api == true`.
