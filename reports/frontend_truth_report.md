# Frontend Truth Report

| Feld | Wert |
|---|---|
| timestamp | `2026-05-18T09:57:14.609538+00:00` |
| collected | 80 |
| passed | 58 |
| failed | 22 |
| skipped | 0 |
| browser | `chromium` |
| api_base_url | `http://127.0.0.1:8000` |
| test_database_url_set | true |
| duration | 568.0s |
| playwright_exit_code | 1 |
| real_api | true |
| mock_only | false |
| api_database_health | true |

## Failed Flows

- `02 Auth bootstrap â€” 05 backend unreachable > shows API_UNREACHABLE error with retry button`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  196 |
  197 |     await page.goto('/documents');
> 198 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 05 backend unreachable > retry button re-triggers bootstrap`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  223 |
  224 |     await page.goto('/documents');
> 225 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 07 forbidden > shows error state on 403 from /auth/me`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  271 |
  272 |     await page.goto('/documents');
> 273 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 07 forbidden > 403 error does not show retry button`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for locator('.state-card--error')[22m


  298 |
  299 |     await page.goto('/documents');
> 300 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                               
- `02 Auth bootstrap â€” 08 logout > after logout, navigating to /documents redirects to login`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByRole('button', { name: 'Abmelden' })[22m
[2m    - locator resolved to <button type="button" class="button-secondary">Abmelden</button>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m    - element is not stable[22m
[2m  - retrying click action[22m
[2m    - waiting for element to be visible, 
- `02 Auth bootstrap â€” 08 logout > after logout, localStorage is cleared`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByRole('button', { name: 'Abmelden' })[22m
[2m    - locator resolved to <button type="button" class="button-secondary">Abmelden</button>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m    - element is not stable[22m
[2m  - retrying click action[22m
[2m    - waiting for element to be visible, 
- `05 Upload flow > shows upload form elements`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('button', { name: 'Dokument importieren' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for getByRole('button', { name: 'Dokument importieren' })[22m


   7 |     await expect(authedPage.getByRole('heading', { name: 'Dokument hochladen' })).toBeVisible();
   8 |     await expect(authedPage
- `05 Upload flow > shows error when submitting without a file`: [31mTest timeout of 45000ms exceeded.[39m Error: locator.click: Test timeout of 45000ms exceeded.
Call log:
[2m  - waiting for getByRole('button', { name: 'Dokument importieren' })[22m
[2m    - locator resolved to <button type="submit">Dokument importieren</button>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m    - element is not stable[22m
[2m  - retrying click action[22m
[2m    - waiting for element to be visible, e
- `05 Upload flow > uploads a text file and completes the import job`: [31mTest timeout of 45000ms exceeded.[39m Error: locator.click: Test timeout of 45000ms exceeded.
Call log:
[2m  - waiting for getByRole('button', { name: 'Dokument importieren' })[22m


  24 |     });
  25 |
> 26 |     await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
     |                                                                            ^
  27 |
  28 |     // Wait for polling to start
  29 |     await expect(
    at H:\WissenMai2026\frontend\tests\g
- `06 Search flow > submitting empty search term shows idle state without error`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByRole('button', { name: 'Suchen' })[22m
[2m    - locator resolved to <button type="submit">Suchen</button>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m    - element is not stable[22m
[2m  - retrying click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m 
- `06 Search flow > search returns results or empty state without error`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByRole('button', { name: 'Suchen' })[22m
[2m    - locator resolved to <button type="submit">Suchen</button>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m  - element was detached from the DOM, retrying[22m


  14 |   test('search returns results or empty state without error', async ({ authedPag
- `06 Search flow > search with workspace context sends request to real backend`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.fill: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByLabel('Suchbegriff')[22m
[2m    - locator resolved to <input value="" type="search" placeholder="z. B. Vertragsentwurf oder Paragraph 5"/>[22m
[2m    - fill("gui truth")[22m
[2m  - attempting fill action[22m
[2m    - waiting for element to be visible, enabled and editable[22m
[2m  - element was detached from the DOM, retrying[22m


  27 |     await expe
- `07 Chat flow > shows chat page heading and workspace context`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumentgestuetzter Chat' })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 10000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumentgestuetzter Chat' })[22m


   5 |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
   6 |     await authedPage.goto('/chat');
>  7 |     await exp
- `07 Chat flow > shows chat composer form`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByLabel('Titel der Sitzung')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for getByLabel('Titel der Sitzung')[22m


  22 |     // Wait for loading to finish
  23 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible({ timeout: 10_000 });
> 24 |     await expect(authedPage.ge
- `07 Chat flow > navigation from documents to chat preserves workspace context`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByRole('link', { name: 'Chat' })[22m
[2m    - locator resolved to <a class="" href="/chat" data-discover="true">Chat</a>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m  - element was detached from the DOM, retrying[22m


  31 |     await expect(authedPage.getByText(`Workspace: ${workspaceId}`))
- `08 Lifecycle GUI > switching back to active filter restores document list`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.selectOption: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByLabel('Statusfilter')[22m


  24 |     await select.selectOption('archived');
  25 |     await authedPage.waitForTimeout(1_000);
> 26 |     await select.selectOption('active');
     |                  ^
  27 |     await authedPage.waitForTimeout(3_000);
  28 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  29 |   });
    a
- `09 Diagnostics GUI > shows system status card`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByText('Systemstatus')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for getByText('Systemstatus')[22m


  12 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  13 |     if (!hasError) {
> 14 |       await expect(authedPage.getByText('Systemstatu
- `09 Diagnostics GUI > shows database status card`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByText('DB Status')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for getByText('DB Status')[22m


  21 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  22 |     if (!hasError) {
> 23 |       await expect(authedPage.getByText('DB Status')).toBe
- `09 Diagnostics GUI > shows migration status card`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByText('Migration Status')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for getByText('Migration Status')[22m


  30 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  31 |     if (!hasError) {
> 32 |       await expect(authedPage.getByText('Mig
- `09 Diagnostics GUI > diagnostics page accessible via admin nav link`: [31mTest timeout of 30000ms exceeded.[39m Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
[2m  - waiting for getByRole('link', { name: 'Admin' })[22m
[2m    - locator resolved to <a class="" data-discover="true" href="/admin/diagnostics">Admin</a>[22m
[2m  - attempting click action[22m
[2m    - waiting for element to be visible, enabled and stable[22m
[2m  - element was detached from the DOM, retrying[22m


  35 |
  36 |   test('diagnostics page accessible via admin
- `10 Workspace bootstrap â€” 01 workspace from membership > workspace id from bootstrap matches injected membership workspace`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 15000ms[22m
[2m  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })[22m


  30 |   test('workspace id from bootstrap matches injected membership workspace', async ({ partialAuthPage }) => {
  31 |     con
- `10 Workspace bootstrap â€” 02 single workspace > single workspace shown as text, no dropdown switcher`: Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('.shell__session').getByText('f1000000-0056-03d1-6f10-58aaed725241')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 5000ms[22m
[2m  - waiting for locator('.shell__session').getByText('f1000000-0056-03d1-6f10-58aaed725241')[22m


  41 |     await expect(authedPage.getByRole('combobox', { name: 'Workspace wechseln' })).no

## Gate-Regeln

- `TEST_DATABASE_URL` muss gesetzt sein.
- `/health/db` der echten API muss erfolgreich sein.
- `collected > 0`, `passed == collected`, `failed == 0`, `skipped == 0`.
- `playwright_exit_code == 0`.
- `mock_only == false` und `real_api == true`.
