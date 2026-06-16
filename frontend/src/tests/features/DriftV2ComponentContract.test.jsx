/**
 * DriftV2ComponentContract.test.jsx
 *
 * Autoritativer Contract-Test für frontend/src/features/drift_v2/DriftDashboard.jsx.
 * Quelle: docs/drift_v2_component_contract.md
 *
 * AKTUELLER STATUS: PARTIAL FAIL
 * 3 testids im Contract weichen von der aktuellen Implementierung ab.
 * Die Implementierung muss migriert werden — nicht dieser Test.
 *
 * Prop-Injection: DriftDashboard akzeptiert useDriftData als Prop.
 * Kein Modul-Mock nötig.
 */

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, it, expect, vi } from 'vitest';
import { DriftDashboard } from '../../features/drift_v2/DriftDashboard.jsx';

afterEach(cleanup);

const MOCK_SUMMARY = {
  workspace_id: 'ws-contract-test',
  latest_run_id: 'run-contract-001',
  latest_run_status: 'completed',
  latest_run_completed_at: '2026-06-15T07:00:00Z',
  total_runs: 5,
  total_findings: 3,
  findings_by_severity: { critical: 1, error: 1, warning: 1, info: 0 },
  findings_by_type: {
    DOCUMENT_DRIFT: 2,
    METADATA_DRIFT: 1,
    LIFECYCLE_DRIFT: 0,
    SOURCE_STATUS_DRIFT: 0,
  },
};

const MOCK_FINDINGS = [
  {
    finding_id: 'f-001',
    severity: 'critical',
    finding_type: 'DOCUMENT_DRIFT',
    entity_id: 'src-001',
    created_at: '2026-06-15T07:00:00Z',
  },
];

function makeHook(overrides = {}) {
  return vi.fn(() => ({
    summary: MOCK_SUMMARY,
    findings: MOCK_FINDINGS,
    loading: false,
    error: null,
    ...overrides,
  }));
}

// ---------------------------------------------------------------------------
// MATCH: testids die bereits korrekt implementiert sind
// ---------------------------------------------------------------------------

describe('DriftV2ComponentContract — Pflicht data-testid (MATCH)', () => {
  it('drift-dashboard: Root-Container vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-dashboard')).toBeInTheDocument();
  });

  it('drift-findings-table: Findings-Tabelle vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-findings-table')).toBeInTheDocument();
  });

  it('drift-filter-severity: Severity-Filter vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-filter-severity')).toBeInTheDocument();
  });

  it('drift-filter-type: Typ-Filter vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-filter-type')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// GAP: testids die im Contract definiert sind, aber in der Implementierung
// unter anderem Namen existieren. Diese Tests FAIL bis DriftDashboard.jsx
// migriert ist.
//
// Erforderliche Umbenennung in DriftDashboard.jsx:
//   drift-last-run-widget          → drift-run-summary
//   drift-severity-breakdown-widget → drift-severity-breakdown
//   drift-type-breakdown-widget    → drift-type-breakdown
//
// ACHTUNG: Umbenennung bricht DriftDashboard.test.jsx — sync migrieren.
// ---------------------------------------------------------------------------

describe('DriftV2ComponentContract — Pflicht data-testid (GAP: Migration erforderlich)', () => {
  it('drift-run-summary: Run-Summary vorhanden [GAP: Impl nutzt drift-last-run-widget]', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    // CONTRACT: data-testid="drift-run-summary"
    // IMPLEMENTIERUNG: data-testid="drift-last-run-widget"
    expect(screen.getByTestId('drift-run-summary')).toBeInTheDocument();
  });

  it('drift-severity-breakdown: Severity-Breakdown vorhanden [GAP: Impl nutzt drift-severity-breakdown-widget]', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    // CONTRACT: data-testid="drift-severity-breakdown"
    // IMPLEMENTIERUNG: data-testid="drift-severity-breakdown-widget"
    expect(screen.getByTestId('drift-severity-breakdown')).toBeInTheDocument();
  });

  it('drift-type-breakdown: Type-Breakdown vorhanden [GAP: Impl nutzt drift-type-breakdown-widget]', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    // CONTRACT: data-testid="drift-type-breakdown"
    // IMPLEMENTIERUNG: data-testid="drift-type-breakdown-widget"
    expect(screen.getByTestId('drift-type-breakdown')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PROHIBIT-02 / PROHIBIT-06: Verbotene Komponenten
// ---------------------------------------------------------------------------

describe('DriftV2ComponentContract — Verbotene Komponenten (PROHIBIT-02, PROHIBIT-06)', () => {
  it('PROHIBIT-02: Kein RepairButton vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByTestId('repair-button')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /repair/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reparier/i })).not.toBeInTheDocument();
  });

  it('PROHIBIT-02: Kein DeleteButton vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByTestId('delete-button')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /löschen/i })).not.toBeInTheDocument();
  });

  it('PROHIBIT-02: Kein ReindexButton vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByTestId('reindex-button')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reindex/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /neuindiz/i })).not.toBeInTheDocument();
  });

  it('PROHIBIT-06: Kein CleanupButton vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByTestId('cleanup-button')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cleanup/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /bereinig/i })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Invarianten
// ---------------------------------------------------------------------------

describe('DriftV2ComponentContract — Invarianten', () => {
  it('DriftDashboard ist importierbar aus drift_v2', async () => {
    const { DriftDashboard: imported } = await import('../../features/drift_v2/DriftDashboard.jsx');
    expect(imported).toBeDefined();
    expect(typeof imported).toBe('function');
  });
});
