/**
 * release_gate_rules.ts
 * Ruflo — Release Gate Regeln (PRI-5)
 *
 * Definiert die vier Freigabestufen mit ihren Schwellwerten und Prüfkriterien.
 * Keine Seiteneffekte. Reine Datenstrukturen und Hilfsfunktionen.
 */

export type GateVerdict = 'BLOCKED' | 'CONDITIONAL_RC' | 'RC_READY' | 'GA_READY';

export type GateCheckId =
  | 'SECURITY_FAIL'
  | 'ID_LEAK'
  | 'GOLD_PATH_MIN'
  | 'GOLD_PATH_GP06'
  | 'PRODUCT_MATURITY'
  | 'CRITICAL_TESTS'
  | 'SECURITY_WARNING'
  | 'LIMITATIONS_DOCUMENTED'
  | 'GOLD_PATH_FULL'
  | 'MATURITY_RC'
  | 'EXPORT_PDF'
  | 'DOCS_CURRENT'
  | 'OPEN_BLOCKERS'
  | 'MATURITY_GA'
  | 'GOLD_PATH_STABLE'
  | 'E2E_COMPLETE'
  | 'PERFORMANCE_ACCEPTED'
  | 'BACKUP_RESTORE_DOCS'
  | 'OPERATIONS_RUNBOOK';

export interface GateRule {
  id: GateCheckId;
  name: string;
  description: string;
  /** Minimaler Wert / Schwellwert. Bei Boolean-Checks: 1 = true, 0 = false erforderlich. */
  threshold: number;
  unit: 'score' | 'count' | 'fraction' | 'boolean' | 'ms' | 's';
  blocking: boolean;
}

export interface GateStage {
  verdict: GateVerdict;
  name: string;
  description: string;
  /** Alle Regeln dieser Stufe müssen PASS sein. */
  requiredRules: GateCheckId[];
  /** Regeln dieser Stufe müssen erfüllt sein ODER als Warning dokumentiert sein. */
  warningRules: GateCheckId[];
}

// ---------------------------------------------------------------------------
// Einzelne Prüfregeln
// ---------------------------------------------------------------------------

export const GATE_RULES: Record<GateCheckId, GateRule> = {
  SECURITY_FAIL: {
    id: 'SECURITY_FAIL',
    name: 'Keine Security-FAIL-Befunde',
    description: 'Kein Befund mit Schweregrad FAIL/CRITICAL im security_hardening_report.',
    threshold: 0,
    unit: 'count',
    blocking: true,
  },
  ID_LEAK: {
    id: 'ID_LEAK',
    name: 'Technische ID-Leaks = 0',
    description: 'technical_id_leak_gate: leaks_found = 0 in UI, Exporten und Reports.',
    threshold: 0,
    unit: 'count',
    blocking: true,
  },
  GOLD_PATH_MIN: {
    id: 'GOLD_PATH_MIN',
    name: 'Gold Path >= 7/8 PASS',
    description: 'Mindestens 7 von 8 Gold-Path-Schritten sind PASS.',
    threshold: 7 / 8,
    unit: 'fraction',
    blocking: true,
  },
  GOLD_PATH_GP06: {
    id: 'GOLD_PATH_GP06',
    name: 'GP-06 (Analyse freigeben) PASS',
    description: 'Sicherheitskritischer Schritt GP-06 muss PASS sein.',
    threshold: 1,
    unit: 'boolean',
    blocking: true,
  },
  PRODUCT_MATURITY: {
    id: 'PRODUCT_MATURITY',
    name: 'Product Maturity >= 80',
    description: 'product_maturity_v3.json score >= 80.',
    threshold: 80,
    unit: 'score',
    blocking: true,
  },
  CRITICAL_TESTS: {
    id: 'CRITICAL_TESTS',
    name: 'Keine kritischen Tests rot',
    description: 'Kein Test mit Marker critical/blocker in failed-State.',
    threshold: 0,
    unit: 'count',
    blocking: true,
  },
  SECURITY_WARNING: {
    id: 'SECURITY_WARNING',
    name: 'Security PASS oder WARNING ohne Blocker',
    description: 'Security darf WARNING haben, wenn kein Befund als BLOCKING_SECURITY eingestuft ist.',
    threshold: 0,
    unit: 'count',
    blocking: false,
  },
  LIMITATIONS_DOCUMENTED: {
    id: 'LIMITATIONS_DOCUMENTED',
    name: 'Bekannte Limitationen dokumentiert',
    description: 'known_limitations.json vorhanden, alle BLOCKING_CORE-Limitationen = 0.',
    threshold: 1,
    unit: 'boolean',
    blocking: false,
  },
  GOLD_PATH_FULL: {
    id: 'GOLD_PATH_FULL',
    name: 'Gold Path 8/8 PASS',
    description: 'Alle 8 Gold-Path-Schritte sind PASS.',
    threshold: 1,
    unit: 'fraction',
    blocking: true,
  },
  MATURITY_RC: {
    id: 'MATURITY_RC',
    name: 'Product Maturity >= 85',
    description: 'product_maturity_v3.json score >= 85.',
    threshold: 85,
    unit: 'score',
    blocking: true,
  },
  EXPORT_PDF: {
    id: 'EXPORT_PDF',
    name: 'Export PDF PASS',
    description: 'export_gold_path.json: GP-07 verdict = PASS.',
    threshold: 1,
    unit: 'boolean',
    blocking: true,
  },
  DOCS_CURRENT: {
    id: 'DOCS_CURRENT',
    name: 'Dokumentation aktuell',
    description: 'documentation_truth_lint.json: alle Checks PASS.',
    threshold: 1,
    unit: 'boolean',
    blocking: true,
  },
  OPEN_BLOCKERS: {
    id: 'OPEN_BLOCKERS',
    name: 'Keine offenen Blocker',
    description: 'rc_final_gate_report: open_blockers = 0.',
    threshold: 0,
    unit: 'count',
    blocking: true,
  },
  MATURITY_GA: {
    id: 'MATURITY_GA',
    name: 'Product Maturity >= 90',
    description: 'product_maturity_v3.json score >= 90.',
    threshold: 90,
    unit: 'score',
    blocking: true,
  },
  GOLD_PATH_STABLE: {
    id: 'GOLD_PATH_STABLE',
    name: 'Gold Path 8/8 stabil (kein Flapping)',
    description: 'Gold Path 8/8 in mindestens 2 aufeinanderfolgenden Läufen.',
    threshold: 2,
    unit: 'count',
    blocking: true,
  },
  E2E_COMPLETE: {
    id: 'E2E_COMPLETE',
    name: 'E2E vollständig',
    description: 'e2e_report.json: alle 8 Flows PASS.',
    threshold: 8,
    unit: 'count',
    blocking: true,
  },
  PERFORMANCE_ACCEPTED: {
    id: 'PERFORMANCE_ACCEPTED',
    name: 'Performance akzeptiert',
    description: 'performance_baseline_report: API p95 < 800ms, Frontend < 3s, keine Memory Leaks.',
    threshold: 1,
    unit: 'boolean',
    blocking: true,
  },
  BACKUP_RESTORE_DOCS: {
    id: 'BACKUP_RESTORE_DOCS',
    name: 'Backup/Restore dokumentiert',
    description: 'docs/operations/backup_restore.md vorhanden und vollständig.',
    threshold: 1,
    unit: 'boolean',
    blocking: true,
  },
  OPERATIONS_RUNBOOK: {
    id: 'OPERATIONS_RUNBOOK',
    name: 'Betriebshandbuch vorhanden',
    description: 'docs/operations/runbook.md vorhanden und vollständig.',
    threshold: 1,
    unit: 'boolean',
    blocking: true,
  },
};

// ---------------------------------------------------------------------------
// Gate-Stufen
// ---------------------------------------------------------------------------

export const GATE_STAGES: GateStage[] = [
  {
    verdict: 'BLOCKED',
    name: 'Blocked',
    description: 'Kritische Kriterien nicht erfüllt. RC nicht möglich.',
    requiredRules: [],
    warningRules: [],
    // BLOCKED wird aktiv, wenn ANY der folgenden Regeln FAIL:
    // SECURITY_FAIL, ID_LEAK, GOLD_PATH_MIN, GOLD_PATH_GP06, PRODUCT_MATURITY, CRITICAL_TESTS
  },
  {
    verdict: 'CONDITIONAL_RC',
    name: 'Conditional RC',
    description: 'RC möglich mit dokumentierten Einschränkungen.',
    requiredRules: [
      'SECURITY_FAIL',    // 0 Security-FAIL-Befunde
      'ID_LEAK',          // 0 Leaks
      'GOLD_PATH_MIN',    // >= 7/8
      'GOLD_PATH_GP06',   // GP-06 PASS
      'PRODUCT_MATURITY', // >= 80
      'CRITICAL_TESTS',   // 0 rote kritische Tests
    ],
    warningRules: [
      'SECURITY_WARNING',
      'LIMITATIONS_DOCUMENTED',
    ],
  },
  {
    verdict: 'RC_READY',
    name: 'RC Ready',
    description: 'Vollständig für Release Candidate bereit.',
    requiredRules: [
      'SECURITY_FAIL',
      'ID_LEAK',
      'GOLD_PATH_FULL',   // 8/8
      'MATURITY_RC',      // >= 85
      'EXPORT_PDF',
      'DOCS_CURRENT',
      'OPEN_BLOCKERS',
      'CRITICAL_TESTS',
    ],
    warningRules: [],
  },
  {
    verdict: 'GA_READY',
    name: 'GA Ready',
    description: 'Bereit für General Availability.',
    requiredRules: [
      'SECURITY_FAIL',
      'ID_LEAK',
      'MATURITY_GA',
      'GOLD_PATH_STABLE',
      'E2E_COMPLETE',
      'PERFORMANCE_ACCEPTED',
      'BACKUP_RESTORE_DOCS',
      'OPERATIONS_RUNBOOK',
      'OPEN_BLOCKERS',
    ],
    warningRules: [],
  },
];

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

/**
 * Gibt die Mindest-Stufe zurück, die ein gegebenes Gate-Ergebnis erreicht.
 * Reihenfolge: GA_READY > RC_READY > CONDITIONAL_RC > BLOCKED
 */
export function getStageDefinition(verdict: GateVerdict): GateStage | undefined {
  return GATE_STAGES.find(s => s.verdict === verdict);
}

export function getBlockingRules(): GateRule[] {
  return Object.values(GATE_RULES).filter(r => r.blocking);
}

/** Formatiert einen Schwellwert lesbar, z.B. fraction 0.875 → "7/8" */
export function formatThreshold(rule: GateRule): string {
  if (rule.unit === 'fraction') {
    const n = Math.round(rule.threshold * 8);
    return `${n}/8`;
  }
  if (rule.unit === 'boolean') return rule.threshold === 1 ? 'PASS' : 'FAIL';
  if (rule.unit === 'ms') return `${rule.threshold} ms`;
  if (rule.unit === 's') return `${rule.threshold} s`;
  return String(rule.threshold);
}
