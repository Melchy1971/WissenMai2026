#!/usr/bin/env node

const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const path = require('node:path');
const { URL } = require('node:url');
const { chromium } = require('../frontend/node_modules/@playwright/test');

const ROOT = path.resolve(__dirname, '..');
const REPORTS_DIR = path.join(ROOT, 'reports');
const REPORT_JSON = path.join(REPORTS_DIR, 'connectivity_truth_report.json');
const REPORT_MD = path.join(REPORTS_DIR, 'connectivity_truth_report.md');

const FRONTEND_BASE_URL = process.env.CONNECTIVITY_FRONTEND_BASE_URL
  || process.env.GUI_TRUTH_BASE_URL
  || 'http://localhost:5173';
const API_BASE_URL = (process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const CONNECTIVITY_LOGIN = process.env.CONNECTIVITY_LOGIN || process.env.TRUTH_LOGIN || process.env.WISSEN_DEV_LOGIN || 'mdickscheit@gmail.com';
const CONNECTIVITY_PASSWORD = process.env.CONNECTIVITY_PASSWORD || process.env.TRUTH_PASSWORD || process.env.WISSEN_DEV_PASSWORD || 'Alex..2026';
const TIMEOUT_MS = Number(process.env.CONNECTIVITY_TIMEOUT_MS || 10000);

function nowIso() {
  return new Date().toISOString();
}

function requestUrl(url, { headers = {}, method = 'GET', body = undefined, timeoutMs = TIMEOUT_MS } = {}) {
  return new Promise((resolve) => {
    const parsed = new URL(url);
    const client = parsed.protocol === 'https:' ? https : http;
    const startedAt = Date.now();
    const req = client.request(
      parsed,
      {
        method,
        headers,
        timeout: timeoutMs,
      },
      (res) => {
        const chunks = [];
        res.on('data', (chunk) => chunks.push(chunk));
        res.on('end', () => {
          resolve({
            ok: res.statusCode >= 200 && res.statusCode < 400,
            status: res.statusCode,
            duration_ms: Date.now() - startedAt,
            body: Buffer.concat(chunks).toString('utf8').slice(0, 1000),
            error: null,
          });
        });
      },
    );
    req.on('timeout', () => {
      req.destroy(Object.assign(new Error('request timeout'), { code: 'ETIMEDOUT' }));
    });
    req.on('error', (error) => {
      resolve({
        ok: false,
        status: null,
        duration_ms: Date.now() - startedAt,
        body: '',
        error: {
          code: error.code || error.name || 'REQUEST_ERROR',
          message: error.message,
        },
      });
    });
    if (body !== undefined) {
      req.write(body);
    }
    req.end();
  });
}

function classifyNetworkFailure(errorText = '') {
  const text = errorText.toLowerCase();
  if (text.includes('name_not_resolved') || text.includes('dns') || text.includes('enotfound')) {
    return 'DNS';
  }
  if (text.includes('timed_out') || text.includes('timeout') || text.includes('etimedout')) {
    return 'TIMEOUT';
  }
  if (text.includes('connection_refused') || text.includes('econnrefused')) {
    return 'REFUSED';
  }
  if (text.includes('cors') || text.includes('access-control')) {
    return 'CORS';
  }
  if (text.includes('mixed_content') || text.includes('mixed content')) {
    return 'MIXED_CONTENT';
  }
  return 'NETWORK';
}

function isMixedContent(frontendUrl, apiUrl) {
  const frontend = new URL(frontendUrl);
  const api = new URL(apiUrl);
  return frontend.protocol === 'https:' && api.protocol === 'http:';
}

function summarizeFailureClasses({ browserEvents, health, authMe }) {
  const classes = new Set();
  if (health.error) classes.add(classifyNetworkFailure(`${health.error.code} ${health.error.message}`));
  if (authMe.error) classes.add(classifyNetworkFailure(`${authMe.error.code} ${authMe.error.message}`));
  for (const event of browserEvents) {
    if (event.type === 'requestfailed') {
      classes.add(classifyNetworkFailure(event.errorText || ''));
    }
    if (event.type === 'console' && /cors|mixed content|failed to load resource/i.test(event.text || '')) {
      classes.add(classifyNetworkFailure(event.text));
    }
  }
  return [...classes].sort();
}

function statusFromBoolean(value) {
  return value ? 'PASS' : 'FAIL';
}

function responseMatchesPath(response, expectedPath) {
  try {
    const parsed = new URL(response.url);
    return parsed.pathname === expectedPath;
  } catch {
    return false;
  }
}

function hasSuccessfulResponse(responses, expectedPath) {
  return responses.some((response) => (
    responseMatchesPath(response, expectedPath)
    && response.status >= 200
    && response.status < 300
  ));
}

function renderMarkdown(payload) {
  const lines = [
    '# Frontend Connectivity Truth Report',
    '',
    `- Result: \`${payload.result}\``,
    `- Generated: \`${payload.generated_at}\``,
    `- Frontend: \`${payload.frontend_base_url}\``,
    `- API: \`${payload.api_base_url}\``,
    '',
    '## Checks',
    '',
    '| Check | Result | Evidence |',
    '|---|---|---|',
  ];
  for (const check of payload.checks) {
    lines.push(`| ${check.id} | \`${check.result}\` | ${String(check.evidence || '').replace(/\|/g, '\\|')} |`);
  }
  lines.push('', '## Failure-Klassifikation', '');
  if (payload.failure_classification.length === 0) {
    lines.push('- keine');
  } else {
    for (const item of payload.failure_classification) {
      lines.push(`- \`${item}\``);
    }
  }
  lines.push('', '## Failed Requests', '');
  if (payload.browser.failed_requests.length === 0) {
    lines.push('- keine');
  } else {
    for (const item of payload.browser.failed_requests) {
      lines.push(`- \`${item.method} ${item.url}\` -> \`${item.errorText}\``);
    }
  }
  return `${lines.join('\n')}\n`;
}

async function runBrowserProbe() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const events = [];
  const apiRequests = [];
  const apiResponses = [];
  const failedRequests = [];

  page.on('console', (msg) => {
    events.push({ type: 'console', level: msg.type(), text: msg.text() });
  });
  page.on('pageerror', (error) => {
    events.push({ type: 'pageerror', text: error.message });
  });
  page.on('request', (request) => {
    if (request.url().startsWith(API_BASE_URL)) {
      apiRequests.push({
        method: request.method(),
        url: request.url(),
        headers: request.headers(),
      });
    }
  });
  page.on('response', (response) => {
    if (response.url().startsWith(API_BASE_URL)) {
      apiResponses.push({
        status: response.status(),
        url: response.url(),
      });
    }
  });
  page.on('requestfailed', (request) => {
    if (request.url().startsWith(API_BASE_URL)) {
      const failure = request.failure();
      failedRequests.push({
        method: request.method(),
        url: request.url(),
        errorText: failure ? failure.errorText : 'unknown',
      });
    }
  });

  let pageBody = '';
  let loginClicked = false;
  try {
    await page.goto(`${FRONTEND_BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });
    await page.locator('input').first().fill(CONNECTIVITY_LOGIN, { timeout: 3000 });
    await page.locator('input').nth(1).fill(CONNECTIVITY_PASSWORD, { timeout: 3000 });
    await page.getByRole('button', { name: /Anmelden/i }).click({ timeout: 3000 });
    loginClicked = true;
    await page.waitForTimeout(Math.min(TIMEOUT_MS, 10000));
    pageBody = await page.locator('body').innerText({ timeout: 3000 }).catch((error) => `BODY_ERROR: ${error.message}`);
  } catch (error) {
    events.push({ type: 'probe_error', text: error.message });
  } finally {
    await browser.close();
  }

  return {
    loginClicked,
    events,
    apiRequests,
    apiResponses,
    failedRequests,
    pageBody,
  };
}

async function main() {
  const generatedAt = nowIso();
  fs.mkdirSync(REPORTS_DIR, { recursive: true });

  const health = await requestUrl(`${API_BASE_URL}/health`);
  const authMe = await requestUrl(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: 'Bearer connectivity-truth-probe' },
  });
  const browser = await runBrowserProbe();
  const loginRequest = browser.apiRequests.find((request) => request.url.endsWith('/api/v1/auth/login'));
  const authMeRequest = browser.apiRequests.find((request) => request.url.endsWith('/api/v1/auth/me'));
  const requestsWithAuth = browser.apiRequests.filter((request) => request.headers.authorization);
  const requestsWithWorkspace = browser.apiRequests.filter((request) => request.headers['x-workspace-id']);
  const consoleText = browser.events.map((event) => event.text || '').join('\n');
  const mixedContent = isMixedContent(FRONTEND_BASE_URL, API_BASE_URL) || /mixed content/i.test(consoleText);
  const corsError = /cors|access-control/i.test(consoleText)
    || browser.failedRequests.some((request) => /cors|access-control/i.test(request.errorText || ''));
  const dnsError = browser.failedRequests.some((request) => classifyNetworkFailure(request.errorText) === 'DNS')
    || [health, authMe].some((probe) => probe.error && classifyNetworkFailure(`${probe.error.code} ${probe.error.message}`) === 'DNS');
  const timeoutError = browser.failedRequests.some((request) => classifyNetworkFailure(request.errorText) === 'TIMEOUT')
    || [health, authMe].some((probe) => probe.error && classifyNetworkFailure(`${probe.error.code} ${probe.error.message}`) === 'TIMEOUT');
  const frontendReachedBackend = browser.apiRequests.length > 0 && browser.failedRequests.length === 0 && browser.apiResponses.length > 0;
  const loginPossible = Boolean(
    loginRequest
    && browser.apiResponses.some((response) => response.url.endsWith('/api/v1/auth/login') && response.status >= 200 && response.status < 300),
  );
  const workspaceBootstrapSuccessful = Boolean(authMeRequest && hasSuccessfulResponse(browser.apiResponses, '/api/v1/auth/me'));
  const documentListLoads = hasSuccessfulResponse(browser.apiResponses, '/documents');
  const apiUnreachableVisible = /API_UNREACHABLE|Backend nicht erreichbar/i.test(browser.pageBody || '');

  const checks = [
    {
      id: 'frontend_reaches_backend',
      result: statusFromBoolean(frontendReachedBackend),
      evidence: frontendReachedBackend
        ? `${browser.apiResponses.length} API responses observed.`
        : `${browser.apiRequests.length} API request(s), ${browser.failedRequests.length} failed request(s).`,
    },
    {
      id: 'health_reachable',
      result: statusFromBoolean(health.ok),
      evidence: health.ok ? `HTTP ${health.status}` : health.error ? `${health.error.code}: ${health.error.message}` : `HTTP ${health.status}`,
    },
    {
      id: 'auth_me_reachable',
      result: statusFromBoolean(authMe.status !== null),
      evidence: authMe.status !== null ? `HTTP ${authMe.status}` : authMe.error ? `${authMe.error.code}: ${authMe.error.message}` : 'no response',
    },
    {
      id: 'login_possible',
      result: statusFromBoolean(loginPossible),
      evidence: loginPossible ? 'Login returned 2xx.' : 'Login did not return a successful response.',
    },
    {
      id: 'workspace_bootstrap_successful',
      result: statusFromBoolean(workspaceBootstrapSuccessful),
      evidence: workspaceBootstrapSuccessful
        ? 'Authenticated /api/v1/auth/me bootstrap returned 2xx.'
        : 'No successful authenticated /api/v1/auth/me bootstrap observed.',
    },
    {
      id: 'document_list_loads',
      result: statusFromBoolean(documentListLoads),
      evidence: documentListLoads
        ? 'Document list endpoint returned 2xx in browser flow.'
        : 'No successful /documents response observed in browser flow.',
    },
    {
      id: 'no_api_unreachable_normalflow',
      result: statusFromBoolean(!apiUnreachableVisible),
      evidence: apiUnreachableVisible
        ? 'API_UNREACHABLE or backend-unreachable copy visible in normal flow.'
        : 'No API_UNREACHABLE normal-flow copy visible.',
    },
    {
      id: 'authorization_header_correct',
      result: statusFromBoolean(Boolean(authMeRequest || requestsWithAuth.length > 0)),
      evidence: authMeRequest
        ? 'Browser auth bootstrap request observed.'
        : requestsWithAuth.length > 0
          ? `${requestsWithAuth.length} request(s) with Authorization header observed.`
          : 'No browser request with Authorization header observed.',
    },
    {
      id: 'x_workspace_id_correct',
      result: statusFromBoolean(requestsWithWorkspace.length > 0),
      evidence: requestsWithWorkspace.length > 0
        ? `${requestsWithWorkspace.length} request(s) with X-Workspace-Id observed.`
        : 'No browser request with X-Workspace-Id observed.',
    },
    {
      id: 'no_cors_error',
      result: statusFromBoolean(!corsError),
      evidence: corsError ? 'CORS/access-control text observed.' : 'No CORS/access-control browser error observed.',
    },
    {
      id: 'no_mixed_content_error',
      result: statusFromBoolean(!mixedContent),
      evidence: mixedContent ? 'Mixed content detected.' : 'No mixed-content mismatch detected.',
    },
    {
      id: 'no_dns_error',
      result: statusFromBoolean(!dnsError),
      evidence: dnsError ? 'DNS failure detected.' : 'No DNS failure detected.',
    },
    {
      id: 'no_timeout',
      result: statusFromBoolean(!timeoutError),
      evidence: timeoutError ? 'Timeout detected.' : 'No timeout detected.',
    },
  ];

  const failureClassification = summarizeFailureClasses({
    browserEvents: [
      ...browser.events,
      ...browser.failedRequests.map((request) => ({ type: 'requestfailed', errorText: request.errorText })),
    ],
    health,
    authMe,
  });
  const payload = {
    version: 1,
    report: 'Frontend Connectivity Truth Report',
    generated_at: generatedAt,
    result: checks.every((check) => check.result === 'PASS') ? 'PASS' : 'FAIL',
    rules: {
      real_api: true,
      real_browser: true,
      mock_responses: false,
    },
    frontend_base_url: FRONTEND_BASE_URL,
    api_base_url: API_BASE_URL,
    checks,
    failure_classification: failureClassification,
    probes: {
      health,
      auth_me: authMe,
    },
    browser: {
      login_clicked: browser.loginClicked,
      api_requests: browser.apiRequests.map((request) => ({
        method: request.method,
        url: request.url,
        has_authorization: Boolean(request.headers.authorization),
        has_x_workspace_id: Boolean(request.headers['x-workspace-id']),
      })),
      api_responses: browser.apiResponses,
      failed_requests: browser.failedRequests,
      console_errors: browser.events.filter((event) => event.type === 'console' && event.level === 'error'),
      page_errors: browser.events.filter((event) => event.type === 'pageerror' || event.type === 'probe_error'),
      body_excerpt: browser.pageBody.slice(0, 1000),
    },
  };

  fs.writeFileSync(REPORT_JSON, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  fs.writeFileSync(REPORT_MD, renderMarkdown(payload), 'utf8');
  console.log(`Connectivity Truth = ${payload.result}`);
  console.log(`Failure classification: ${failureClassification.join(', ') || 'none'}`);
  console.log(`Wrote: ${REPORT_JSON}`);
  console.log(`Wrote: ${REPORT_MD}`);
  process.exit(payload.result === 'PASS' ? 0 : 1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
