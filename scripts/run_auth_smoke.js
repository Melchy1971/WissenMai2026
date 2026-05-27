#!/usr/bin/env node

const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { chromium } = require('../frontend/node_modules/@playwright/test');

const ROOT = path.resolve(__dirname, '..');
const REPORTS_DIR = path.join(ROOT, 'reports');
const CURRENT_DIR = path.join(REPORTS_DIR, 'current');
const SEED_REPORT = path.join(CURRENT_DIR, 'seed_smoke_report.json');
const AUTH_REPORT = path.join(CURRENT_DIR, 'auth_smoke_report.json');
const PYTHON = path.join(ROOT, 'backend', '.venv', 'Scripts', 'python.exe');
const LOGIN = 'mdickscheit@gmail.com';
const PASSWORD = 'Alex..2026';
const WORKSPACE_ID = '00000000-0000-0000-0000-000000000001';
const USER_ID = '00000000-0000-0000-0000-000000000001';
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
  env.DATABASE_URL = env.DATABASE_URL || '';
  env.WISSEN_DEV_LOGIN = LOGIN;
  env.WISSEN_DEV_PASSWORD = PASSWORD;
  env.DEFAULT_USER_ID = USER_ID;
  env.DEFAULT_WORKSPACE_ID = WORKSPACE_ID;
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

function requestJson(url, { method = 'GET', headers = {}, body = undefined } = {}) {
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

function runSeed(env) {
  const result = spawnSync(PYTHON, ['scripts/seed_auth.py'], {
    cwd: path.join(ROOT, 'backend'),
    env,
    encoding: 'utf8',
  });
  return {
    ok: result.status === 0,
    exit_code: result.status,
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

function querySeedState(env) {
  const code = `
import json, os, sys
sys.path.insert(0, os.path.join(${JSON.stringify(ROOT)}, "backend"))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models.documents import User, Workspace, WorkspaceMembership
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
with Session(engine) as session:
    user = session.scalar(select(User).where(User.login == ${JSON.stringify(LOGIN)}))
    workspace = session.scalar(select(Workspace).where(Workspace.id == ${JSON.stringify(WORKSPACE_ID)}))
    membership = None
    if user and workspace:
        membership = session.scalar(select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id, WorkspaceMembership.workspace_id == workspace.id))
    print(json.dumps({
        "user": None if user is None else {"id": user.id, "login": user.login, "is_active": user.is_active, "is_default": user.is_default},
        "workspace": None if workspace is None else {"id": workspace.id, "name": workspace.name, "is_default": workspace.is_default},
        "membership": None if membership is None else {"workspace_id": membership.workspace_id, "user_id": membership.user_id, "role": membership.role},
    }))
engine.dispose()
`;
  const result = spawnSync(PYTHON, ['-c', code], { cwd: ROOT, env, encoding: 'utf8' });
  if (result.status !== 0) {
    return { ok: false, error: result.stderr || result.stdout };
  }
  return { ok: true, state: JSON.parse(result.stdout) };
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
  page.on('console', (msg) => events.push({ type: 'console', level: msg.type(), text: msg.text() }));
  page.on('pageerror', (error) => events.push({ type: 'pageerror', text: error.message }));
  let body = '';
  let url = '';
  let leftLoginScreen = false;
  try {
    await page.goto(`${FRONTEND_BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.locator('input').first().fill(LOGIN, { timeout: 5000 });
    await page.locator('input').nth(1).fill(PASSWORD, { timeout: 5000 });
    await page.getByRole('button', { name: /Anmelden/i }).click({ timeout: 5000 });
    await page.waitForTimeout(3000);
    url = page.url();
    body = await page.locator('body').innerText({ timeout: 5000 });
    leftLoginScreen = !url.includes('/login') && !/Anmelden/.test(body);
  } catch (error) {
    events.push({ type: 'probe_error', text: error.message });
  } finally {
    await browser.close();
  }
  return { left_login_screen: leftLoginScreen, final_url: url, body_excerpt: body.slice(0, 1000), events };
}

async function main() {
  fs.mkdirSync(CURRENT_DIR, { recursive: true });
  const env = loadEnv();
  const errors = [];

  const seedRun = runSeed(env);
  if (!seedRun.ok) errors.push('seed_auth.py failed');
  const seedState = querySeedState(env);
  if (!seedState.ok) errors.push('seed DB state query failed');

  const state = seedState.state || {};
  const seedChecks = [
    { id: 'seed_auth_runs_without_error', pass: seedRun.ok },
    { id: 'users_contains_login', pass: state.user?.login === LOGIN },
    { id: 'is_active_true', pass: state.user?.is_active === true },
    { id: 'workspace_exists', pass: Boolean(state.workspace?.id) },
    { id: 'membership_role_admin', pass: state.membership?.role === ROLE },
  ];
  for (const check of seedChecks) {
    if (!check.pass) errors.push(check.id);
  }

  fs.writeFileSync(SEED_REPORT, `${JSON.stringify({
    generated_at: nowIso(),
    database_url: maskDatabaseUrl(env.DATABASE_URL),
    result: seedChecks.every((check) => check.pass) ? 'PASS' : 'FAIL',
    seed_stdout: seedRun.stdout,
    seed_stderr: seedRun.stderr,
    checks: seedChecks,
    state,
  }, null, 2)}\n`, 'utf8');

  const backend = startProcess(PYTHON, ['-m', 'uvicorn', '--app-dir', 'backend', 'app.main:app', '--host', '127.0.0.1', '--port', '8001'], env, 'auth_smoke_backend.log');
  const frontendEnv = { ...env, VITE_API_BASE_URL: API_BASE_URL };
  const frontend = startProcess('cmd.exe', ['/c', 'npm.cmd', '--prefix', 'frontend', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '5174'], frontendEnv, 'auth_smoke_frontend.log');

  try {
    const health = await waitFor(`${API_BASE_URL}/health`);
    const frontendReady = await waitFor(FRONTEND_BASE_URL);
    const login = await requestJson(`${API_BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login: LOGIN, password: PASSWORD }),
    });
    const token = login.json?.token;
    const me = token
      ? await requestJson(`${API_BASE_URL}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      : { ok: false, status: null, error: 'missing login token' };
    const browser = await runBrowserProbe();

    const authChecks = [
      { id: 'backend_health_reachable', pass: Boolean(health.status && health.status < 500), evidence: health.status || health.error },
      { id: 'frontend_reachable', pass: Boolean(frontendReady.status && frontendReady.status < 500), evidence: frontendReady.status || frontendReady.error },
      { id: 'login_successful', pass: login.ok && Boolean(token), evidence: login.status || login.error },
      { id: 'auth_me_returns_user_and_workspace', pass: me.ok && me.json?.user?.login === LOGIN && Array.isArray(me.json?.memberships) && me.json.memberships.some((item) => item.workspace_id === WORKSPACE_ID && item.role === ROLE), evidence: me.status || me.error },
      { id: 'frontend_leaves_login_screen', pass: browser.left_login_screen, evidence: browser.final_url },
    ];
    for (const check of authChecks) {
      if (!check.pass) errors.push(check.id);
    }

    fs.writeFileSync(AUTH_REPORT, `${JSON.stringify({
      generated_at: nowIso(),
      api_base_url: API_BASE_URL,
      frontend_base_url: FRONTEND_BASE_URL,
      result: authChecks.every((check) => check.pass) ? 'PASS' : 'FAIL',
      checks: authChecks,
      login_response: { status: login.status, user: login.json?.user || null, memberships: login.json?.memberships || null, active_workspace_id: login.json?.active_workspace_id || null },
      auth_me_response: { status: me.status, user: me.json?.user || null, memberships: me.json?.memberships || null, active_workspace_id: me.json?.active_workspace_id || null },
      browser,
      remaining_errors: errors,
    }, null, 2)}\n`, 'utf8');
  } finally {
    backend.kill();
    frontend.kill();
  }

  console.log(`Wrote ${SEED_REPORT}`);
  console.log(`Wrote ${AUTH_REPORT}`);
  console.log(`Remaining errors: ${errors.length ? errors.join(', ') : 'none'}`);
  process.exit(errors.length ? 1 : 0);
}

main().catch((error) => {
  fs.mkdirSync(CURRENT_DIR, { recursive: true });
  fs.writeFileSync(AUTH_REPORT, `${JSON.stringify({ generated_at: nowIso(), result: 'FAIL', fatal_error: error.stack || error.message }, null, 2)}\n`, 'utf8');
  console.error(error);
  process.exit(1);
});
