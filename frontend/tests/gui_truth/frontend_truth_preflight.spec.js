import { test, expect } from '@playwright/test';
import fs from 'fs';

const PRECONDITIONS = [
  {
    name: 'Frontend erreichbar',
    check: async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('title')).not.toHaveCount(0, { timeout: 10000 });
    },
  },
  {
    name: 'Backend erreichbar',
    check: async ({ request }) => {
      const res = await request.get('/health');
      expect(res.status()).toBe(200);
    },
  },
  {
    name: '/health ok',
    check: async ({ request }) => {
      const res = await request.get('/health');
      const json = await res.json();
      expect(json.status).toBe('ok');
    },
  },
  {
    name: 'Seed User loginfähig',
    check: async ({ request }) => {
      const login = process.env.TRUTH_LOGIN;
      const password = process.env.TRUTH_PASSWORD;
      const res = await request.post('/auth/login', {
        data: { login, password },
      });
      expect(res.status()).toBe(200);
      const json = await res.json();
      expect(json.token).toBeTruthy();
    },
  },
  {
    name: '/auth/me liefert Workspace',
    check: async ({ request }) => {
      const login = process.env.TRUTH_LOGIN;
      const password = process.env.TRUTH_PASSWORD;
      const loginRes = await request.post('/auth/login', {
        data: { login, password },
      });
      const { token } = await loginRes.json();
      const meRes = await request.get('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(meRes.status()).toBe(200);
      const me = await meRes.json();
      expect(me.active_workspace_id).toBeTruthy();
    },
  },
  {
    name: 'Dokumentliste erreichbar',
    check: async ({ request }) => {
      const login = process.env.TRUTH_LOGIN;
      const password = process.env.TRUTH_PASSWORD;
      const loginRes = await request.post('/auth/login', {
        data: { login, password },
      });
      const { token } = await loginRes.json();
      const docsRes = await request.get('/documents', {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(docsRes.status()).toBe(200);
      const docs = await docsRes.json();
      expect(Array.isArray(docs)).toBeTruthy();
    },
  },
  {
    name: 'Testdaten erzeugbar',
    check: async ({ request }) => {
      const login = process.env.TRUTH_LOGIN;
      const password = process.env.TRUTH_PASSWORD;
      const loginRes = await request.post('/auth/login', {
        data: { login, password },
      });
      const { token } = await loginRes.json();
      const createRes = await request.post('/documents', {
        headers: { Authorization: `Bearer ${token}` },
        data: { title: 'Preflight Test', content: 'fail-fast-check', type: 'note' },
      });
      expect([200, 201]).toContain(createRes.status());
    },
  },
];

test('frontend-truth preflight', async ({ page, request }) => {
  const results = [];
  for (const pre of PRECONDITIONS) {
    try {
      await pre.check({ page, request });
      results.push({ name: pre.name, ok: true });
    } catch (e) {
      results.push({ name: pre.name, ok: false, error: e.message || String(e) });
      break; // Fail-fast
    }
  }
  const allOk = results.every(r => r.ok);
  const report = {
    name: 'frontend_truth_preflight',
    timestamp: new Date().toISOString(),
    result: allOk ? 'PASS' : 'FAIL',
    checks: results,
    failed: results.filter(r => !r.ok).length,
    passed: results.filter(r => r.ok).length,
    errors: results.filter(r => !r.ok).map(r => r.error),
    gate: 'frontend_truth',
    exit_code: allOk ? 0 : 1,
    blockers: allOk ? [] : results.filter(r => !r.ok).map(r => ({ reason: r.error, check: r.name })),
    known_limitations: [],
  };
  fs.writeFileSync('test-results/frontend_truth_preflight.json', JSON.stringify(report, null, 2));
  expect(allOk).toBeTruthy();
});
