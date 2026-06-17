/**
 * release_gate_evaluator.test.ts
 * Unit-Tests für den Release Gate Evaluator.
 * Ausführen: npx ts-node --esm node_modules/.bin/vitest run scripts/release_gate/
 */

import { describe, it, expect } from 'vitest';
import { evaluate } from './release_gate_evaluator.js';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BLOCKED_INPUTS = {
  productMaturity: 52,
  goldPathPassed: 4,
  goldPathTotal: 8,
  gp06Pass: false,
  idLeaks: 0,
  securityFailCount: 0,
  criticalTestsFailed: 0,
  limitationsDocumented: true,
  exportPdfPass: false,
  docsCurrentPass: true,
  openBlockers: 3,
  e2eFlowsPassed: 0,
  performanceAccepted: false,
  backupRestoreDocsExist: false,
  operationsRunbookExists: false,
  goldPathStableRuns: 0,
};

const CONDITIONAL_RC_INPUTS = {
  productMaturity: 82,
  goldPathPassed: 7,
  goldPathTotal: 8,
  gp06Pass: true,
  idLeaks: 0,
  securityFailCount: 0,
  criticalTestsFailed: 0,
  limitationsDocumented: true,
  exportPdfPass: true,
  docsCurrentPass: true,
  openBlockers: 1,
  e2eFlowsPassed: 5,
  performanceAccepted: false,
  backupRestoreDocsExist: false,
  operationsRunbookExists: false,
  goldPathStableRuns: 1,
};

const RC_READY_INPUTS = {
  productMaturity: 87,
  goldPathPassed: 8,
  goldPathTotal: 8,
  gp06Pass: true,
  idLeaks: 0,
  securityFailCount: 0,
  criticalTestsFailed: 0,
  limitationsDocumented: true,
  exportPdfPass: true,
  docsCurrentPass: true,
  openBlockers: 0,
  e2eFlowsPassed: 8,
  performanceAccepted: true,
  backupRestoreDocsExist: true,
  operationsRunbookExists: true,
  goldPathStableRuns: 2,
};

const GA_READY_INPUTS = {
  ...RC_READY_INPUTS,
  productMaturity: 92,
  goldPathStableRuns: 3,
};

// ---------------------------------------------------------------------------
// Tests — Blocked
// ---------------------------------------------------------------------------

describe('BLOCKED scenarios', () => {
  it('gibt BLOCKED bei Score 52 < 80', () => {
    const r = evaluate(BLOCKED_INPUTS);
    expect(r.verdict).toBe('BLOCKED');
  });

  it('gibt BLOCKED wenn GP-06 FAIL', () => {
    const r = evaluate({ ...RC_READY_INPUTS, gp06Pass: false });
    expect(r.verdict).toBe('BLOCKED');
  });

  it('gibt BLOCKED bei ID-Leaks > 0', () => {
    const r = evaluate({ ...RC_READY_INPUTS, idLeaks: 3 });
    expect(r.verdict).toBe('BLOCKED');
  });

  it('gibt BLOCKED bei Security-FAIL-Befunden', () => {
    const r = evaluate({ ...RC_READY_INPUTS, securityFailCount: 2 });
    expect(r.verdict).toBe('BLOCKED');
  });

  it('gibt BLOCKED wenn kritische Tests rot', () => {
    const r = evaluate({ ...RC_READY_INPUTS, criticalTestsFailed: 1 });
    expect(r.verdict).toBe('BLOCKED');
  });

  it('gibt BLOCKED wenn Gold Path < 7/8', () => {
    const r = evaluate({ ...RC_READY_INPUTS, goldPathPassed: 5, gp06Pass: true });
    expect(r.verdict).toBe('BLOCKED');
  });

  it('blocked_by enthält die fehlenden Regeln', () => {
    const r = evaluate(BLOCKED_INPUTS);
    const ids = r.blocked_by.map(c => c.id);
    expect(ids).toContain('PRODUCT_MATURITY');
    expect(ids).toContain('GOLD_PATH_MIN');
    expect(ids).toContain('GOLD_PATH_GP06');
  });
});

// ---------------------------------------------------------------------------
// Tests — CONDITIONAL_RC
// ---------------------------------------------------------------------------

describe('CONDITIONAL_RC scenarios', () => {
  it('gibt CONDITIONAL_RC bei Score 82, GP 7/8, GP-06 PASS', () => {
    const r = evaluate(CONDITIONAL_RC_INPUTS);
    expect(r.verdict).toBe('CONDITIONAL_RC');
  });

  it('gibt CONDITIONAL_RC wenn open_blockers > 0', () => {
    const r = evaluate({ ...RC_READY_INPUTS, openBlockers: 2 });
    // OPEN_BLOCKERS ist required für RC_READY, nicht für CONDITIONAL_RC
    expect(r.verdict).toBe('CONDITIONAL_RC');
  });
});

// ---------------------------------------------------------------------------
// Tests — RC_READY
// ---------------------------------------------------------------------------

describe('RC_READY scenarios', () => {
  it('gibt RC_READY bei Score 87, GP 8/8, open_blockers 0', () => {
    const r = evaluate(RC_READY_INPUTS);
    expect(r.verdict).toBe('RC_READY');
  });

  it('gibt RC_READY nicht wenn Dokumentation nicht aktuell', () => {
    const r = evaluate({ ...RC_READY_INPUTS, docsCurrentPass: false });
    expect(r.verdict).toBe('CONDITIONAL_RC');
  });

  it('gibt RC_READY nicht ohne Export-PDF-PASS', () => {
    const r = evaluate({ ...RC_READY_INPUTS, exportPdfPass: false });
    expect(r.verdict).toBe('CONDITIONAL_RC');
  });
});

// ---------------------------------------------------------------------------
// Tests — GA_READY
// ---------------------------------------------------------------------------

describe('GA_READY scenarios', () => {
  it('gibt GA_READY bei Score 92, stabiler Gold Path, E2E 8/8', () => {
    const r = evaluate(GA_READY_INPUTS);
    expect(r.verdict).toBe('GA_READY');
  });

  it('gibt nicht GA_READY wenn Backup-Docs fehlen', () => {
    const r = evaluate({ ...GA_READY_INPUTS, backupRestoreDocsExist: false });
    expect(r.verdict).toBe('RC_READY');
  });

  it('gibt nicht GA_READY wenn E2E < 8', () => {
    const r = evaluate({ ...GA_READY_INPUTS, e2eFlowsPassed: 6 });
    expect(r.verdict).toBe('RC_READY');
  });
});

// ---------------------------------------------------------------------------
// Tests — Summary
// ---------------------------------------------------------------------------

describe('Summary-Felder', () => {
  it('zählt blocking_failures korrekt', () => {
    const r = evaluate(BLOCKED_INPUTS);
    expect(r.summary.blocking_failures).toBeGreaterThan(0);
  });

  it('total_checks entspricht Anzahl Regeln', () => {
    const r = evaluate(RC_READY_INPUTS);
    expect(r.summary.total_checks).toBe(19);
  });

  it('passed + failed + missing = total_checks', () => {
    const r = evaluate(RC_READY_INPUTS);
    expect(r.summary.passed + r.summary.failed + r.summary.missing).toBe(r.summary.total_checks);
  });

  it('missing enthält Regeln ohne Input', () => {
    const sparse = { idLeaks: 0, securityFailCount: 0 };
    const r = evaluate(sparse);
    expect(r.missing.length).toBeGreaterThan(0);
  });
});
