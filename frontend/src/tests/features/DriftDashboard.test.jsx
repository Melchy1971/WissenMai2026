import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DriftDashboard } from '../../features/drift_v2/DriftDashboard.jsx';

afterEach(cleanup);

// ---------------------------------------------------------------------------
// Mock data factories
// ---------------------------------------------------------------------------

const MOCK_SUMMARY = {
  workspace_id: 'ws-test',
  latest_run_id: 'run-abc-123',
  latest_run_status: 'completed',
  latest_run_completed_at: '2026-06-11T10:00:00Z',
  total_runs: 3,
  total_findings: 5,
  findings_by_type: {
    DOCUMENT_DRIFT: 2,
    METADATA_DRIFT: 2,
    LIFECYCLE_DRIFT: 1,
    SOURCE_STATUS_DRIFT: 0,
  },
  findings_by_severity: {
    critical: 0,
    error: 2,
    warning: 2,
    info: 1,
  },
  critical_count: 0,
  error_count: 2,
};

const MOCK_FINDINGS = [
  {
    finding_id: 'f-001',
    run_id: 'run-abc-123',
    workspace_id: 'ws-test',
    finding_type: 'DOCUMENT_DRIFT',
    severity: 'error',
    entity_type: 'document',
    entity_id: 'doc-001',
    created_at: '2026-06-11T09:00:00Z',
  },
  {
    finding_id: 'f-002',
    run_id: 'run-abc-123',
    workspace_id: 'ws-test',
    finding_type: 'METADATA_DRIFT',
    severity: 'warning',
    entity_type: 'document',
    entity_id: 'doc-002',
    created_at: '2026-06-11T09:01:00Z',
  },
];

function makeMockHook(overrides = {}) {
  return vi.fn(() => ({
    summary: MOCK_SUMMARY,
    findings: MOCK_FINDINGS,
    loading: false,
    error: null,
    ...overrides,
  }));
}

// ---------------------------------------------------------------------------
// Test 1: Dashboard sichtbar
// ---------------------------------------------------------------------------

describe('DriftDashboard - Sichtbarkeit', () => {
  it('rendert das Dashboard', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-dashboard')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 2: Letzter Drift Run sichtbar
// ---------------------------------------------------------------------------

describe('DriftDashboard - Letzter Drift Run', () => {
  it('zeigt das Last-Run-Widget', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-last-run-widget')).toBeInTheDocument();
  });

  it('zeigt run_id an', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-last-run-id').textContent).toBe('run-abc-123');
  });

  it('zeigt Meldung wenn kein Run vorhanden', () => {
    const hook = makeMockHook({
      summary: { ...MOCK_SUMMARY, latest_run_id: null, latest_run_status: null, latest_run_completed_at: null },
    });
    render(<DriftDashboard useDriftData={hook} />);
    expect(screen.getByTestId('drift-no-run-message')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 3: Severity Breakdown sichtbar
// ---------------------------------------------------------------------------

describe('DriftDashboard - Severity Breakdown', () => {
  it('zeigt das Severity-Breakdown-Widget', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-severity-breakdown-widget')).toBeInTheDocument();
  });

  it('zeigt alle vier Severity-Werte', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    for (const sev of ['critical', 'error', 'warning', 'info']) {
      expect(screen.getByTestId(`drift-severity-${sev}`)).toBeInTheDocument();
    }
  });
});

// ---------------------------------------------------------------------------
// Test 4: Drift Type Breakdown sichtbar
// ---------------------------------------------------------------------------

describe('DriftDashboard - Type Breakdown', () => {
  it('zeigt das Type-Breakdown-Widget', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-type-breakdown-widget')).toBeInTheDocument();
  });

  it('zeigt alle vier Finding-Typen', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    for (const t of ['DOCUMENT_DRIFT', 'METADATA_DRIFT', 'LIFECYCLE_DRIFT', 'SOURCE_STATUS_DRIFT']) {
      expect(screen.getByTestId(`drift-type-${t}`)).toBeInTheDocument();
    }
  });
});

// ---------------------------------------------------------------------------
// Test 5: Findings Tabelle sichtbar
// ---------------------------------------------------------------------------

describe('DriftDashboard - Findings Tabelle', () => {
  it('zeigt die Findings-Tabelle', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-findings-table')).toBeInTheDocument();
  });

  it('zeigt Finding-Rows', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    const rows = screen.getAllByTestId('drift-finding-row');
    expect(rows.length).toBe(2);
  });

  it('zeigt Meldung wenn keine Findings', () => {
    render(<DriftDashboard useDriftData={makeMockHook({ findings: [] })} />);
    expect(screen.getByTestId('drift-no-findings-message')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 6: Filter Severity funktioniert
// ---------------------------------------------------------------------------

describe('DriftDashboard - Filter Severity', () => {
  it('zeigt die Severity-Filter-Dropdown', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-filter-severity')).toBeInTheDocument();
  });

  it('ruft useDriftData mit Severity-Filter auf wenn Auswahl geaendert', () => {
    const hook = makeMockHook();
    render(<DriftDashboard useDriftData={hook} />);
    fireEvent.change(screen.getByTestId('drift-filter-severity'), { target: { value: 'error' } });
    expect(hook).toHaveBeenCalledWith(expect.objectContaining({ severityFilter: 'error' }));
  });
});

// ---------------------------------------------------------------------------
// Test 7: Filter Type funktioniert
// ---------------------------------------------------------------------------

describe('DriftDashboard - Filter Type', () => {
  it('zeigt die Type-Filter-Dropdown', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.getByTestId('drift-filter-type')).toBeInTheDocument();
  });

  it('ruft useDriftData mit Type-Filter auf wenn Auswahl geaendert', () => {
    const hook = makeMockHook();
    render(<DriftDashboard useDriftData={hook} />);
    fireEvent.change(screen.getByTestId('drift-filter-type'), { target: { value: 'METADATA_DRIFT' } });
    expect(hook).toHaveBeenCalledWith(expect.objectContaining({ typeFilter: 'METADATA_DRIFT' }));
  });
});

// ---------------------------------------------------------------------------
// Test 8: Keine Repair Buttons
// ---------------------------------------------------------------------------

describe('DriftDashboard - Keine Repair Buttons (PROHIBIT-02)', () => {
  it('hat keinen Button mit Text "Repair" oder "Reparieren"', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    const buttons = screen.queryAllByRole('button');
    for (const btn of buttons) {
      const text = btn.textContent.toLowerCase();
      expect(text).not.toContain('repair');
      expect(text).not.toContain('reparier');
    }
  });

  it('hat kein Element mit data-testid "repair"', () => {
    const { container } = render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(container.querySelector('[data-testid*="repair"]')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Test 9: Keine Cleanup Buttons
// ---------------------------------------------------------------------------

describe('DriftDashboard - Keine Cleanup Buttons (PROHIBIT-06)', () => {
  it('hat keinen Button mit Text "Cleanup" oder "Bereinigen"', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    const buttons = screen.queryAllByRole('button');
    for (const btn of buttons) {
      const text = btn.textContent.toLowerCase();
      expect(text).not.toContain('cleanup');
      expect(text).not.toContain('bereinig');
    }
  });

  it('hat kein Element mit data-testid "cleanup"', () => {
    const { container } = render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(container.querySelector('[data-testid*="cleanup"]')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Test 10: API Fehler wird korrekt angezeigt
// ---------------------------------------------------------------------------

describe('DriftDashboard - API Fehler Anzeige', () => {
  it('zeigt das Error-Element bei API-Fehler', () => {
    const hook = makeMockHook({
      summary: null,
      findings: [],
      error: 'API nicht erreichbar',
    });
    render(<DriftDashboard useDriftData={hook} />);
    expect(screen.getByTestId('drift-api-error')).toBeInTheDocument();
  });

  it('zeigt die Fehlermeldung an', () => {
    const hook = makeMockHook({
      summary: null,
      findings: [],
      error: 'API nicht erreichbar',
    });
    render(<DriftDashboard useDriftData={hook} />);
    expect(screen.getByTestId('drift-api-error').textContent).toContain('API nicht erreichbar');
  });

  it('hat role=alert am Fehler-Element', () => {
    const hook = makeMockHook({ summary: null, findings: [], error: 'Fehler' });
    render(<DriftDashboard useDriftData={hook} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('zeigt kein Fehler-Element wenn kein Fehler', () => {
    render(<DriftDashboard useDriftData={makeMockHook()} />);
    expect(screen.queryAllByTestId('drift-api-error').length).toBe(0);
  });
});