#!/usr/bin/env node

const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { chromium } = require('../frontend/node_modules/@playwright/test');

const ROOT = path.resolve(__dirname, '..');
const REPORTS_DIR = path.join(ROOT, 'reports');
const CURRENT_DIR = path.join(REPORTS_DIR, 'current');
const JSON_REPORT = path.join(CURRENT_DIR, 'runtime_connectivity_report.json');
const MD_REPORT = path.join(CURRENT_DIR, 'runtime_connectivity_report.md');
const PYTHON = path.join(ROOT, 'backend', '.venv', 'Scripts', 'python.exe');
const LOGIN = 'mdickscheit@gmail.com';
const PASSWORD = 'Alex..2026';
const WORKSPACE_ID = '00000000-0000-0000-0000-000000000001';
const ROLE = 'admin';
const API_BASE_URL = 'http://127.0.0.1:8001';
const FRONTEND_BASE_URL = 'http://127.0.0.1:5174';

function loadEnv() {
  const env = { ...process.env };
  const envPath = path.join(ROOT, '.env');
  if (fs.existsSync(envPath)) {
    for (const rawLine of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#') || !line.includes('=')) continue;
      const [key, ...rest] = line.split('=');
      if (!env[key]) env[key] = rest.join('=');
    }
  }
  env.WISSEN_DEV_LOGIN = LOGIN;
  env.WISSEN_DEV_PASSWORD = PASSWORD;
  env.DEFAULT_WORKSPACE_ID = WORKSPACE_ID;
  env.DEFAULT_USER_ID = WORKSPACE_ID;
  return env;
}

function nowIso() {
  return new Date().toISOString();
}

function maskDatabaseUrl(url) {
  if (!url || !url.includes('@')) return url || '';
  const [credentials, host] = url.split('@');
  const [scheme, userInfo] = credentials.split('://');
  const user = (userInfo || '').split(':')[0];
  return `${scheme}://${user}:***@${host}`;
}

function requestJson(url, { method = 'GET', headers = {}, body } = {}) {
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const req = http.request(url, { method, headers, timeout: 10000 }, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null;
        try {
          json = text ? JSON.parse(text) : null;
        } catch {
          json = null;
        }
        resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, json, text, duration_ms: Date.now() - startedAt });
      });
    });
    req.on('timeout', () => req.destroy(new Error('request timeout')));
    req.on('error', (error) => resolve({ ok: false, status: null, json: null, text: '', error: error.message, duration_ms: Date.now() - startedAt }));
    if (body !== undefined) req.write(body);
    req.end();
  });
}

async function waitFor(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = await requestJson(url);
    if (last.ok || last.status) return last;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return last || { ok: false, status: null, error: 'timeout' };
}

function run(command, args, env, cwd = ROOT) {
  const result = spawnSync(command, args, { cwd, env, encoding: 'utf8' });
  return {
    ok: result.status === 0,
    exit_code: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
  };
}

function parseRevisionLines(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split(/\s+/)[0])
    .filter((value) => /^[0-9a-fA-F_]+$/.test(value));
}

function checkAlembic(env) {
  const heads = run(PYTHON, ['-m', 'alembic', '-c', path.join(ROOT, 'backend', 'alembic.ini'), 'heads'], env, ROOT);
  const current = run(PYTHON, ['-m', 'alembic', '-c', path.join(ROOT, 'backend', 'alembic.ini'), 'current'], env, ROOT);
  const headRevisions = parseRevisionLines(heads.stdout);
  const currentRevisions = parseRevisionLines(current.stdout);
  const missing = headRevisions.filter((revision) => !currentRevisions.includes(revision));
  return {
    ok: heads.ok && current.ok && headRevisions.length > 0 && missing.length === 0,
    heads: headRevisions,
    current: currentRevisions,
    missing_heads: missing,
    stdout: { heads: heads.stdout, current: current.stdout },
    stderr: { heads: heads.stderr, current: current.stderr },
  };
}

function runSeed(env) {
  return run(PYTHON, ['scripts/seed_auth.py'], env, path.join(ROOT, 'backend'));
}

function startProcess(command, args, env, logName) {
  const log = fs.openSync(path.join(REPORTS_DIR, logName), 'a');
  return spawn(command, args, {
    cwd: ROOT,
    env,
    stdio: ['ignore', log, log],
    windowsHide: true,
  });
}

async function runBrowserProbe() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const events = [];
  const apiResponses = [];
  page.on('console', (msg) => events.push({ type: 'console', level: msg.type(), text: msg.text() }));
  page.on('pageerror', (error) => events.push({ type: 'pageerror', text: error.message }));
  page.on('response', (response) => {
    if (response.url().startsWith(API_BASE_URL)) {
      apiResponses.push({ url: response.url(), status: response.status() });
    }
  });

  let finalUrl = '';
  let body = '';
  let workspaceBootstrapSuccessful = false;
  try {
    await page.goto(`${FRONTEND_BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.locator('input').first().fill(LOGIN, { timeout: 5000 });
    await page.locator('input').nth(1).fill(PASSWORD, { timeout: 5000 });
    await page.getByRole('button', { name: /Anmelden/i }).click({ timeout: 5000 });
    await page.waitForTimeout(3000);
    finalUrl = page.url();
    body = await page.locator('body').innerText({ timeout: 5000 });
    workspaceBootstrapSuccessful = body.includes(WORKSPACE_ID) && !finalUrl.includes('/login');
  } catch (error) {
    events.push({ type: 'probe_error', text: error.message });
  } finally {
    await browser.close();
  }

  return {
    frontend_api_reachable: apiResponses.some((item) => item.status >= 200 && item.status < 300),
    workspace_bootstrap_successful: workspaceBootstrapSuccessful,
    final_url: finalUrl,
    api_responses: apiResponses,
    body_excerpt: body.slice(0, 1000),
    events,
  };
}

function renderMarkdown(report) {
  const lines = [
    '# Runtime Connectivity Report',
    '',
    `- Result: \`${report.result}\``,
    `- Generated: \`${report.generated_at}\``,
    `- Database: \`${report.database_url}\``,
    `- API: \`${report.api_base_url}\``,
    `- Frontend: \`${report.frontend_base_url}\``,
    '',
    '## Checks',
    '',
    '| Check | Result | Evidence |',
    '|---|---:|---|',
  ];
  for (const check of report.checks) {
    lines.push(`| ${check.id} | \`${check.result}\` | ${String(check.evidence || '').replace(/\|/g, '\\|')} |`);
  }
  lines.push('', '## Alembic', '');
  lines.push(`- Heads: \`${report.alembic.heads.join(', ') || '<none>'}\``);
  lines.push(`- Current: \`${report.alembic.current.join(', ') || '<none>'}\``);
  lines.push('', '## Verbleibende Fehler', '');
  if (report.remaining_errors.length === 0) {
    lines.push('- keine');
  } else {
    for (const error of report.remaining_errors) lines.push(`- ${error}`);
  }
  return `${lines.join('\n')}\n`;
}

async function main() {
  fs.mkdirSync(CURRENT_DIR, { recursive: true });
  const env = loadEnv();
  const remainingErrors = [];
  const databaseUrlSet = Boolean(env.DATABASE_URL && env.DATABASE_URL.trim());

  const alembic = databaseUrlSet ? checkAlembic(env) : { ok: false, heads: [], current: [], missing_heads: ['DATABASE_URL missing'] };
  const seed = databaseUrlSet ? runSeed(env) : { ok: false, stdout: '', stderr: 'DATABASE_URL missing' };
  if (!databaseUrlSet) remainingErrors.push('DATABASE_URL missing');
  if (!alembic.ok) remainingErrors.push('Alembic current is not at all heads');
  if (!seed.ok) remainingErrors.push('seed_auth.py failed');

  const backend = startProcess(PYTHON, ['-m', 'uvicorn', '--app-dir', 'backend', 'app.main:app', '--host', '127.0.0.1', '--port', '8001'], env, 'runtime_backend.log');
  const frontendEnv = { ...env, VITE_API_BASE_URL: API_BASE_URL };
  const frontend = startProcess('cmd.exe', ['/c', 'npm.cmd', '--prefix', 'frontend', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '5174'], frontendEnv, 'runtime_frontend.log');

  let health = { ok: false, status: null };
  let login = { ok: false, status: null };
  let me = { ok: false, status: null };
  let browser = { frontend_api_reachable: false, workspace_bootstrap_successful: false, final_url: '', api_responses: [], events: [] };
  try {
    health = await waitFor(`${API_BASE_URL}/health`);
    await waitFor(FRONTEND_BASE_URL);
    login = await requestJson(`${API_BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login: LOGIN, password: PASSWORD }),
    });
    const token = login.json?.token;
    me = token ? await requestJson(`${API_BASE_URL}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } }) : { ok: false, status: null, error: 'missing login token' };
    browser = await runBrowserProbe();
  } finally {
    backend.kill();
    frontend.kill();
  }

  const meHasUserWorkspace = me.ok
    && me.json?.user?.login === LOGIN
    && Array.isArray(me.json?.memberships)
    && me.json.memberships.some((item) => item.workspace_id === WORKSPACE_ID && item.role === ROLE);

  const checks = [
    { id: 'DATABASE_URL gesetzt', pass: databaseUrlSet, evidence: databaseUrlSet ? maskDatabaseUrl(env.DATABASE_URL) : 'missing' },
    { id: 'Alembic head', pass: alembic.ok, evidence: alembic.ok ? `current=${alembic.current.join(', ')}` : `missing=${(alembic.missing_heads || []).join(', ')}` },
    { id: 'Seed erfolgreich', pass: seed.ok, evidence: seed.ok ? 'seed_auth.py exit 0' : seed.stderr },
    { id: 'Backend /health', pass: health.ok, evidence: health.status || health.error },
    { id: '/auth/login', pass: login.ok && Boolean(login.json?.token), evidence: login.status || login.error },
    { id: '/auth/me', pass: meHasUserWorkspace, evidence: me.status || me.error },
    { id: 'Frontend API erreichbar', pass: browser.frontend_api_reachable, evidence: `${browser.api_responses.length} API response(s)` },
    { id: 'Workspace Bootstrap erfolgreich', pass: browser.workspace_bootstrap_successful, evidence: browser.final_url },
  ];
  for (const check of checks) {
    if (!check.pass && !remainingErrors.includes(check.id)) remainingErrors.push(check.id);
  }

  const report = {
    report_schema_version: 1,
    report_name: 'runtime_connectivity_report',
    generated_by: 'gate_validator',
    generated_at: nowIso(),
    timestamp: null,
    result: checks.every((check) => check.pass) ? 'PASS' : 'FAIL',
    status: null,
    gate: 'runtime_connectivity_gate',
    environment: 'local',
    report_type: 'truth',
    collected: checks.length,
    passed: checks.filter((check) => check.pass).length,
    failed: checks.filter((check) => !check.pass).length,
    errors: 0,
    skipped: 0,
    exit_code: checks.every((check) => check.pass) ? 0 : 1,
    blockers: [],
    source_command: 'node scripts/run_runtime_connectivity_report.js',
    database_url: maskDatabaseUrl(env.DATABASE_URL),
    api_base_url: API_BASE_URL,
    frontend_base_url: FRONTEND_BASE_URL,
    credentials: { login: LOGIN },
    checks: checks.map((check) => ({ id: check.id, result: check.pass ? 'PASS' : 'FAIL', evidence: check.evidence })),
    alembic,
    seed: { exit_code: seed.exit_code, stdout: seed.stdout, stderr: seed.stderr },
    health: { status: health.status, ok: health.ok, error: health.error || null },
    login: { status: login.status, ok: login.ok, user: login.json?.user || null, memberships: login.json?.memberships || null },
    auth_me: { status: me.status, ok: me.ok, user: me.json?.user || null, memberships: me.json?.memberships || null, active_workspace_id: me.json?.active_workspace_id || null },
    frontend: browser,
    remaining_errors: remainingErrors,
  };
  report.timestamp = report.generated_at;
  report.status = report.result;
  report.blockers = checks
    .filter((check) => !check.pass)
    .map((check) => ({ id: check.id, severity: 'blocking', reason: String(check.evidence || 'failed') }));

  fs.writeFileSync(JSON_REPORT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(MD_REPORT, renderMarkdown(report), 'utf8');
  console.log(`Runtime Connectivity = ${report.result}`);
  console.log(`Wrote: ${JSON_REPORT}`);
  console.log(`Wrote: ${MD_REPORT}`);
  console.log(`Remaining errors: ${remainingErrors.join(', ') || 'none'}`);
  process.exit(report.result === 'PASS' ? 0 : 1);
}

main().catch((error) => {
  fs.mkdirSync(CURRENT_DIR, { recursive: true });
  const report = { generated_at: nowIso(), result: 'FAIL', fatal_error: error.stack || error.message, remaining_errors: [error.message] };
  fs.writeFileSync(JSON_REPORT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(MD_REPORT, renderMarkdown({ ...report, database_url: '', api_base_url: API_BASE_URL, frontend_base_url: FRONTEND_BASE_URL, checks: [], alembic: { heads: [], current: [] } }), 'utf8');
  console.error(error);
  process.exit(1);
});
