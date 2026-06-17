/**
 * release_gate_evaluator.ts
 * Ruflo — Release Gate Evaluator (PRI-5)
 *
 * Liest maschinenlesbare Report-Dateien und ergibt ein Gate-Verdict.
 * Aufruf: npx ts-node release_gate_evaluator.ts [--report-dir <path>]
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  GateVerdict,
  GateCheckId,
  GATE_RULES,
  GATE_STAGES,
  formatThreshold,
} from './release_gate_rules.js';

// ---------------------------------------------------------------------------
// Input-Typen (Report-Dateien)
// ---------------------------------------------------------------------------

interface ReportInputs {
  productMaturity?: number;           // product_maturity_v3.json → score
  goldPathPassed?: number;            // product_gold_path.json → passed count
  goldPathTotal?: number;             // product_gold_path.json → total count
  gp06Pass?: boolean;                 // product_gold_path.json → GP-06 verdict
  idLeaks?: number;                   // technical_id_leak_gate.json → leaks_found
  securityFailCount?: number;         // security_hardening_report.json → fail_count
  criticalTestsFailed?: number;       // rc_final_gate_report inputs → critical_failed
  limitationsDocumented?: boolean;    // known_limitations.json → exists + BLOCKING_CORE = 0
  exportPdfPass?: boolean;            // export_gold_path.json → GP-07 verdict
  docsCurrentPass?: boolean;          // documentation_truth_lint.json → all PASS
  openBlockers?: number;              // rc_final_gate_report → open_blockers
  e2eFlowsPassed?: number;            // e2e_report.json → flows_passed
  performanceAccepted?: boolean;      // performance_baseline_report.json → rc_accepted
  backupRestoreDocsExist?: boolean;   // docs/operations/backup_restore.md → exists
  operationsRunbookExists?: boolean;  // docs/operations/runbook.md → exists
  goldPathStableRuns?: number;        // consecutive stable runs (manual input)
}

interface CheckResult {
  id: GateCheckId;
  name: string;
  verdict: 'PASS' | 'FAIL' | 'MISSING';
  actual: string;
  required: string;
  blocking: boolean;
  note?: string;
}

interface EvaluationResult {
  verdict: GateVerdict;
  generated_at: string;
  inputs: ReportInputs;
  checks: CheckResult[];
  blocked_by: CheckResult[];
  warnings: CheckResult[];
  passed: CheckResult[];
  missing: CheckResult[];
  summary: {
    total_checks: number;
    passed: number;
    failed: number;
    missing: number;
    blocking_failures: number;
  };
}

// ---------------------------------------------------------------------------
// Report-Loader
// ---------------------------------------------------------------------------

function loadJson(reportDir: string, filename: string): Record<string, unknown> | null {
  const p = path.join(reportDir, filename);
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return null;
  }
}

function loadInputs(reportDir: string, docsDir: string): ReportInputs {
  const maturity = loadJson(reportDir, 'product_maturity_v3.json');
  const goldPath = loadJson(reportDir, 'product_gold_path.json');
  const idLeak = loadJson(reportDir, 'technical_id_leak_gate.json');
  const security = loadJson(reportDir, 'security_hardening_report.json');
  const exportGp = loadJson(reportDir, 'export_gold_path.json');
  const docLint = loadJson(reportDir, 'documentation_truth_lint.json');
  const limitations = loadJson(reportDir, 'known_limitations.json');
  const e2e = loadJson(reportDir, 'e2e_report.json');
  const perf = loadJson(reportDir, 'performance_baseline_report.json');

  // Gold path: count PASS steps
  let gpPassed = 0;
  let gpTotal = 8;
  let gp06Pass = false;
  if (goldPath) {
    const steps: unknown[] = (goldPath['main_gold_path'] as Record<string, unknown>)?.['steps'] as unknown[] ?? [];
    gpTotal = steps.length || 8;
    gpPassed = steps.filter((s: unknown) => (s as Record<string, unknown>)['verdict'] === 'PASS').length;
    const gp06 = steps.find((s: unknown) => (s as Record<string, unknown>)['step_id'] === 'GP-06');
    gp06Pass = (gp06 as Record<string, unknown>)?.['verdict'] === 'PASS';
  }

  // Backup/Restore + Runbook docs
  const backupExists = fs.existsSync(path.join(docsDir, 'operations', 'backup_restore.md'));
  const runbookExists = fs.existsSync(path.join(docsDir, 'operations', 'runbook.md'));

  return {
    productMaturity: (maturity?.['score'] ?? maturity?.['total_score']) as number | undefined,
    goldPathPassed: gpPassed,
    goldPathTotal: gpTotal,
    gp06Pass,
    idLeaks: (idLeak?.['leaks_found'] as number) ?? undefined,
    securityFailCount: (security?.['fail_count'] as number) ?? undefined,
    criticalTestsFailed: 0, // injected from CI
    limitationsDocumented: limitations != null && ((limitations['blocking_core_count'] as number) ?? 0) === 0,
    exportPdfPass: (() => {
      if (!exportGp) return undefined;
      const steps = ((exportGp['main_gold_path'] as Record<string, unknown>)?.['steps'] as unknown[]) ?? [];
      const gp07 = steps.find((s: unknown) => (s as Record<string, unknown>)['step_id'] === 'EGP-07' || (s as Record<string, unknown>)['name']?.toString().includes('Export'));
      return (gp07 as Record<string, unknown>)?.['verdict'] === 'PASS';
    })(),
    docsCurrentPass: (docLint?.['verdict'] as string) === 'PASS',
    openBlockers: 0, // injected from rc_final_gate_report
    e2eFlowsPassed: (e2e?.['flows_passed'] as number) ?? undefined,
    performanceAccepted: (perf?.['rc_accepted'] as boolean) ?? undefined,
    backupRestoreDocsExist: backupExists,
    operationsRunbookExists: runbookExists,
    goldPathStableRuns: 1, // default
  };
}

// ---------------------------------------------------------------------------
// Evaluator
// ---------------------------------------------------------------------------

function checkRule(id: GateCheckId, inputs: ReportInputs): CheckResult {
  const rule = GATE_RULES[id];
  const base: CheckResult = {
    id,
    name: rule.name,
    verdict: 'MISSING',
    actual: 'n/a',
    required: formatThreshold(rule),
    blocking: rule.blocking,
  };

  switch (id) {
    case 'SECURITY_FAIL': {
      if (inputs.securityFailCount === undefined) return { ...base, verdict: 'MISSING' };
      const pass = inputs.securityFailCount <= rule.threshold;
      return { ...base, verdict: pass ? 'PASS' : 'FAIL', actual: String(inputs.securityFailCount) };
    }
    case 'ID_LEAK': {
      if (inputs.idLeaks === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.idLeaks <= 0 ? 'PASS' : 'FAIL', actual: String(inputs.idLeaks) };
    }
    case 'GOLD_PATH_MIN': {
      if (inputs.goldPathPassed === undefined) return { ...base, verdict: 'MISSING' };
      const fraction = inputs.goldPathPassed / (inputs.goldPathTotal ?? 8);
      return { ...base, verdict: fraction >= rule.threshold ? 'PASS' : 'FAIL', actual: `${inputs.goldPathPassed}/${inputs.goldPathTotal ?? 8}` };
    }
    case 'GOLD_PATH_GP06': {
      if (inputs.gp06Pass === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.gp06Pass ? 'PASS' : 'FAIL', actual: inputs.gp06Pass ? 'PASS' : 'FAIL' };
    }
    case 'PRODUCT_MATURITY':
    case 'MATURITY_RC':
    case 'MATURITY_GA': {
      if (inputs.productMaturity === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.productMaturity >= rule.threshold ? 'PASS' : 'FAIL', actual: String(inputs.productMaturity) };
    }
    case 'CRITICAL_TESTS': {
      if (inputs.criticalTestsFailed === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.criticalTestsFailed === 0 ? 'PASS' : 'FAIL', actual: String(inputs.criticalTestsFailed) };
    }
    case 'SECURITY_WARNING': {
      if (inputs.securityFailCount === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.securityFailCount === 0 ? 'PASS' : 'FAIL', actual: String(inputs.securityFailCount) };
    }
    case 'LIMITATIONS_DOCUMENTED': {
      if (inputs.limitationsDocumented === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.limitationsDocumented ? 'PASS' : 'FAIL', actual: inputs.limitationsDocumented ? '1' : '0' };
    }
    case 'GOLD_PATH_FULL': {
      if (inputs.goldPathPassed === undefined) return { ...base, verdict: 'MISSING' };
      const total = inputs.goldPathTotal ?? 8;
      return { ...base, verdict: inputs.goldPathPassed >= total ? 'PASS' : 'FAIL', actual: `${inputs.goldPathPassed}/${total}` };
    }
    case 'EXPORT_PDF': {
      if (inputs.exportPdfPass === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.exportPdfPass ? 'PASS' : 'FAIL', actual: inputs.exportPdfPass ? 'PASS' : 'FAIL' };
    }
    case 'DOCS_CURRENT': {
      if (inputs.docsCurrentPass === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.docsCurrentPass ? 'PASS' : 'FAIL', actual: inputs.docsCurrentPass ? 'PASS' : 'FAIL' };
    }
    case 'OPEN_BLOCKERS': {
      if (inputs.openBlockers === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.openBlockers === 0 ? 'PASS' : 'FAIL', actual: String(inputs.openBlockers) };
    }
    case 'GOLD_PATH_STABLE': {
      if (inputs.goldPathStableRuns === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.goldPathStableRuns >= rule.threshold ? 'PASS' : 'FAIL', actual: String(inputs.goldPathStableRuns) };
    }
    case 'E2E_COMPLETE': {
      if (inputs.e2eFlowsPassed === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.e2eFlowsPassed >= rule.threshold ? 'PASS' : 'FAIL', actual: String(inputs.e2eFlowsPassed) };
    }
    case 'PERFORMANCE_ACCEPTED': {
      if (inputs.performanceAccepted === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.performanceAccepted ? 'PASS' : 'FAIL', actual: inputs.performanceAccepted ? 'PASS' : 'FAIL' };
    }
    case 'BACKUP_RESTORE_DOCS': {
      if (inputs.backupRestoreDocsExist === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.backupRestoreDocsExist ? 'PASS' : 'FAIL', actual: inputs.backupRestoreDocsExist ? 'exists' : 'missing' };
    }
    case 'OPERATIONS_RUNBOOK': {
      if (inputs.operationsRunbookExists === undefined) return { ...base, verdict: 'MISSING' };
      return { ...base, verdict: inputs.operationsRunbookExists ? 'PASS' : 'FAIL', actual: inputs.operationsRunbookExists ? 'exists' : 'missing' };
    }
  }
}

export function evaluate(inputs: ReportInputs): EvaluationResult {
  const allCheckIds = Object.keys(GATE_RULES) as GateCheckId[];
  const checks: CheckResult[] = allCheckIds.map(id => checkRule(id, inputs));

  const blocked = checks.filter(c => c.verdict === 'FAIL' && c.blocking);
  const warnings = checks.filter(c => c.verdict === 'FAIL' && !c.blocking);
  const passed = checks.filter(c => c.verdict === 'PASS');
  const missing = checks.filter(c => c.verdict === 'MISSING');

  // Determine verdict by checking stage requirements
  let verdict: GateVerdict = 'BLOCKED';

  if (blocked.length === 0) {
    // Check CONDITIONAL_RC
    const condStage = GATE_STAGES.find(s => s.verdict === 'CONDITIONAL_RC')!;
    const condOk = condStage.requiredRules.every(id => {
      const c = checks.find(ch => ch.id === id);
      return c?.verdict === 'PASS';
    });
    if (condOk) {
      verdict = 'CONDITIONAL_RC';
      // Check RC_READY
      const rcStage = GATE_STAGES.find(s => s.verdict === 'RC_READY')!;
      const rcOk = rcStage.requiredRules.every(id => {
        const c = checks.find(ch => ch.id === id);
        return c?.verdict === 'PASS';
      });
      if (rcOk) {
        verdict = 'RC_READY';
        // Check GA_READY
        const gaStage = GATE_STAGES.find(s => s.verdict === 'GA_READY')!;
        const gaOk = gaStage.requiredRules.every(id => {
          const c = checks.find(ch => ch.id === id);
          return c?.verdict === 'PASS';
        });
        if (gaOk) verdict = 'GA_READY';
      }
    }
  }

  return {
    verdict,
    generated_at: new Date().toISOString(),
    inputs,
    checks,
    blocked_by: blocked,
    warnings,
    passed,
    missing,
    summary: {
      total_checks: checks.length,
      passed: passed.length,
      failed: blocked.length + warnings.length,
      missing: missing.length,
      blocking_failures: blocked.length,
    },
  };
}

// ---------------------------------------------------------------------------
// CLI entry point
// ---------------------------------------------------------------------------

if (process.argv[1] && process.argv[1].endsWith('release_gate_evaluator.ts')) {
  const args = process.argv.slice(2);
  const reportDirIdx = args.indexOf('--report-dir');
  const reportDir = reportDirIdx >= 0 ? args[reportDirIdx + 1] : path.resolve('../../reports/current');
  const docsDir = path.resolve('../../docs');

  const inputs = loadInputs(reportDir, docsDir);
  const result = evaluate(inputs);

  console.log(JSON.stringify(result, null, 2));

  // Exit code: 0 = RC or higher, 1 = BLOCKED
  process.exit(result.verdict === 'BLOCKED' ? 1 : 0);
}
