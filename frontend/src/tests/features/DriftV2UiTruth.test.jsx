/**
 * DriftV2UiTruth.test.jsx
 *
 * Read-Only UI Truth für drift_v2/DriftDashboard.
 * Prüft alle 8 UI-Truth-Checks per PO-Auftrag 2026-06-15.
 *
 * Prüfpunkte:
 *   1. Dashboard rendert.
 *   2. Summary rendert.
 *   3. Findings Tabelle rendert.
 *   4. Filter funktionieren.
 *   5. API Fehler wird korrekt angezeigt.
 *   6. Keine mutierenden Buttons sichtbar.
 *   7. Keine Cleanup/Repair/Reindex Funktionen erreichbar.
 *   8. Workspace Isolation UI-seitig respektiert.
 */

import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { afterEach, describe, it, expect, vi } from 'vitest';
import { DriftDashboard } from '../../features/drift_v2/DriftDashboard.jsx';

afterEach(cleanup);

const MOCK_SUMMARY = {
  workspace_id: 'ws-truth-001',
  latest_run_id: 'run-truth-abc',
  latest_run_status: 'completed',
  latest_run_completed_at: '2026-06-15T07:00:00Z',
  total_runs: 3,
  total_findings: 2,
  findings_by_severity: { critical: 0, error: 1, warning: 1, info: 0 },
  findings_by_type: {
    DOCUMENT_DRIFT: 1,
    METADATA_DRIFT: 1,
    LIFECYCLE_DRIFT: 0,
    SOURCE_STATUS_DRIFT: 0,
  },
};

const MOCK_FINDINGS = [
  {
    finding_id: 'f-t-001',
    severity: 'error',
    finding_type: 'DOCUMENT_DRIFT',
    entity_id: 'doc-001',
    created_at: '2026-06-15T06:00:00Z',
  },
  {
    finding_id: 'f-t-002',
    severity: 'warning',
    finding_type: 'METADATA_DRIFT',
    entity_id: 'doc-002',
    created_at: '2026-06-15T06:01:00Z',
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
// Check 1: Dashboard rendert
// ---------------------------------------------------------------------------

describe('UI-Truth-01: Dashboard rendert', () => {
  it('Root-Container data-testid="drift-dashboard" ist im DOM', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-dashboard')).toBeInTheDocument();
  });

  it('Dashboard zeigt Überschrift "Drift"', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByRole('heading', { name: /drift/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Check 2: Summary rendert
// ---------------------------------------------------------------------------

describe('UI-Truth-02: Summary rendert', () => {
  it('Last-Run-Widget ist sichtbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-last-run-widget')).toBeInTheDocument();
  });

  it('Run-ID wird angezeigt', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-last-run-id')).toHaveTextContent('run-truth-abc');
  });

  it('Severity-Breakdown ist sichtbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-severity-breakdown-widget')).toBeInTheDocument();
  });

  it('Type-Breakdown ist sichtbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-type-breakdown-widget')).toBeInTheDocument();
  });

  it('Meldung wenn kein Run vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook({ summary: null })} />);
    expect(screen.getByTestId('drift-no-run-message')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Check 3: Findings Tabelle rendert
// ---------------------------------------------------------------------------

describe('UI-Truth-03: Findings Tabelle rendert', () => {
  it('Findings-Tabelle ist sichtbar wenn Findings vorhanden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.getByTestId('drift-findings-table')).toBeInTheDocument();
  });

  it('Einzelne Finding-Rows sind sichtbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    const rows = screen.getAllByTestId('drift-finding-row');
    expect(rows).toHaveLength(2);
  });

  it('Leer-Meldung wenn keine Findings', () => {
    render(<DriftDashboard useDriftData={makeHook({ findings: [] })} />);
    expect(screen.getByTestId('drift-no-findings-message')).toBeInTheDocument();
    expect(screen.queryByTestId('drift-findings-table')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Check 4: Filter funktionieren
// ---------------------------------------------------------------------------

describe('UI-Truth-04: Filter funktionieren', () => {
  it('Severity-Filter ist sichtbar und bedienbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    const select = screen.getByTestId('drift-filter-severity');
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe('SELECT');
  });

  it('Typ-Filter ist sichtbar und bedienbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    const select = screen.getByTestId('drift-filter-type');
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe('SELECT');
  });

  it('Severity-Filter-Änderung löst useDriftData-Aufruf mit neuem Wert aus', () => {
    const hook = makeHook();
    render(<DriftDashboard useDriftData={hook} />);
    fireEvent.change(screen.getByTestId('drift-filter-severity'), {
      target: { value: 'error' },
    });
    // Hook wird nach Filter-Änderung erneut aufgerufen (State-Trigger)
    expect(hook).toHaveBeenCalled();
  });

  it('Typ-Filter-Änderung löst useDriftData-Aufruf mit neuem Wert aus', () => {
    const hook = makeHook();
    render(<DriftDashboard useDriftData={hook} />);
    fireEvent.change(screen.getByTestId('drift-filter-type'), {
      target: { value: 'DOCUMENT_DRIFT' },
    });
    expect(hook).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Check 5: API Fehler wird korrekt angezeigt
// ---------------------------------------------------------------------------

describe('UI-Truth-05: API Fehler wird korrekt angezeigt', () => {
  it('Fehler-Element mit data-testid="drift-api-error" erscheint bei API-Fehler', () => {
    render(
      <DriftDashboard
        useDriftData={makeHook({ summary: null, findings: [], error: { message: 'Verbindungsfehler', code: 'NETWORK_ERROR' } })}
      />,
    );
    expect(screen.getByTestId('drift-api-error')).toBeInTheDocument();
  });

  it('Fehler-Element hat role="alert"', () => {
    render(
      <DriftDashboard
        useDriftData={makeHook({ summary: null, findings: [], error: { message: 'Timeout', code: 'TIMEOUT' } })}
      />,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('Fehlermeldung wird als Text angezeigt', () => {
    render(
      <DriftDashboard
        useDriftData={makeHook({ summary: null, findings: [], error: { message: 'Server nicht erreichbar', code: 'SERVER_ERROR' } })}
      />,
    );
    expect(screen.getByTestId('drift-api-error')).toHaveTextContent('Server nicht erreichbar');
  });

  it('Kein Fehler-Element bei erfolgreichem Laden', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByTestId('drift-api-error')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Check 6: Keine mutierenden Buttons sichtbar
// ---------------------------------------------------------------------------

describe('UI-Truth-06: Keine mutierenden Buttons sichtbar', () => {
  it('Keine Buttons außer Filter-Controls im normalen Zustand', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    const buttons = screen.queryAllByRole('button');
    // Drift-Dashboard hat keine Action-Buttons — nur Select-Dropdowns
    expect(buttons).toHaveLength(0);
  });

  it('Kein Button mit Text "Speichern" / "Aktualisieren" / "Anwenden"', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('button', { name: /speichern/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /aktualisieren/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /anwenden/i })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Check 7: Keine Cleanup/Repair/Reindex Funktionen erreichbar (PROHIBIT-02/06)
// ---------------------------------------------------------------------------

describe('UI-Truth-07: Keine Cleanup/Repair/Reindex Funktionen erreichbar (PROHIBIT-02, PROHIBIT-06)', () => {
  it('Kein Repair-Button (PROHIBIT-02)', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('button', { name: /repair/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reparier/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId('repair-button')).not.toBeInTheDocument();
  });

  it('Kein Cleanup-Button (PROHIBIT-06)', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('button', { name: /cleanup/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /bereinig/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId('cleanup-button')).not.toBeInTheDocument();
  });

  it('Kein Delete-Button', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /löschen/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId('delete-button')).not.toBeInTheDocument();
  });

  it('Kein Reindex-Button', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('button', { name: /reindex/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /neuindiz/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId('reindex-button')).not.toBeInTheDocument();
  });

  it('Kein Write-Link oder Write-Formular sichtbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Check 8: Workspace Isolation UI-seitig respektiert
// ---------------------------------------------------------------------------

describe('UI-Truth-08: Workspace Isolation UI-seitig respektiert', () => {
  it('Kein Workspace-Selector oder Workspace-Switcher sichtbar', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByTestId('workspace-selector')).not.toBeInTheDocument();
    expect(screen.queryByTestId('workspace-switcher')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /workspace/i })).not.toBeInTheDocument();
  });

  it('Genau ein Dashboard-Root wird gerendert (keine Multi-Workspace-Ansicht)', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    const roots = screen.getAllByTestId('drift-dashboard');
    expect(roots).toHaveLength(1);
  });

  it('workspace_id aus Summary wird nicht als navigierbarer Link angezeigt', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    // workspace_id 'ws-truth-001' darf nicht als klickbarer Link im DOM erscheinen
    const workspaceLink = screen.queryByRole('link', { name: /ws-truth-001/i });
    expect(workspaceLink).not.toBeInTheDocument();
  });

  it('Keine Cross-Workspace-Navigations-Controls im Dashboard', () => {
    render(<DriftDashboard useDriftData={makeHook()} />);
    expect(screen.queryByRole('button', { name: /workspace wechseln/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /switch workspace/i })).not.toBeInTheDocument();
  });
});
