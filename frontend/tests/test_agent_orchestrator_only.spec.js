import { test, expect } from '@playwright/test';

test('Agent-UI startet keinen direkten Tool-Aufruf', async ({ page }) => {
  await page.route('**/api/v1/agents', route =>
    route.fulfill({ json: { items: [{ id: 'ag1', name: 'Planner', type: 'planner', status: 'idle' }] } })
  );
  await page.route('**/api/v1/agents/executions', route =>
    route.fulfill({ json: { items: [] } })
  );
  await page.route('**/api/v1/agents/ag1', route =>
    route.fulfill({ json: { id: 'ag1', name: 'Planner', limits: {}, execution_plan: null } })
  );
  await page.goto('/agents');
  await page.getByText('Planner').click();
  const runButton = page.getByRole('button', { name: /Ausführen/i });
  await expect(runButton).toBeVisible();
  // Klick zeigt Hinweis auf Orchestrator, führt kein direktes Tool aus
  page.once('dialog', dialog => {
    expect(dialog.message()).toContain('Orchestrator');
    dialog.dismiss();
  });
  await runButton.click();
});
