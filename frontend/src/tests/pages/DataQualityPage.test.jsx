import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../auth/AuthContext.jsx';
import { DataQualityPage } from '../../pages/DataQualityPage.jsx';
import * as dqApi from '../../api/dataQuality.js';

afterEach(cleanup);

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const WORKSPACE_ID = 'ws-test-001';
const RUN_ID = 'run-abc-123';

function makeSummary(overrides = {}) {
  return {
    workspace_id: WORKSPACE_ID,
    latest_run_id: RUN_ID,
    latest_run_status: 'completed',
    latest_run_at: '2026-06-01T08:00:00Z',
    latest_quality_score: 87.5,
    total_runs: 3,
    total_findings: 4,
    findings_by_severity: { error: 1, warning: 3 },
    findings_by_type: { DUPLICATE_DOCUMENT: 2, INVALID_LIFECYCLE: 2 },
    ...overrides,
  };
}

function makeRun(overrides = {}) {
  return {
    run_id: RUN_ID,
    workspace_id: WORKSPACE_ID,
    status: 'completed',
    started_at: '2026-06-01T08:00:00Z',
    finished_at: '2026-06-01T08:01:00Z',
    total_findings: 4,
    quality_score: 87.5,
    created_by: null,
    finding_counts: { DUPLICATE_DOCUMENT: 2, INVALID_LIFECYCLE: 2 },
    ...overrides,
  };
}

function makeFindings(count = 2) {
  return {
    items: Array.from({ length: count }, (_, i) => ({
      finding_id: `f-${i}`,
      run_id: RUN_ID,
      workspace_id: WORKSPACE_ID,
      finding_type: 'DUPLICATE_DOCUMENT',
      severity: 'warning',
      document_id: `doc-${i}`,
      version_id: null,
      chunk_id: null,
      title: `Duplikat ${i}`,
      description: `doc-${i} teilt content_hash`,
      remediation: 'Dokumente prüfen und ggf. zusammenführen',
      created_at: '2026-06-01T08:00:00Z',
    })),
    total: count,
    limit: 50,
    offset: 0,
  };
}

const authState = {
  token: 'tok',
  user: null,
  active_workspace_id: WORKSPACE_ID,
  memberships: [{ workspace_id: WORKSPACE_ID, role: 'member' }],
};

function renderPage(authOverrides = {}) {
  const auth = { ...authState, ...authOverrides };
  return render(
    <AuthProvider initialState={auth}>
      <MemoryRouter initialEntries={['/data-quality']}>
        <Routes>
          <Route path="/data-quality" element={<DataQualityPage />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

describe('DataQualityPage — loading', () => {
  it('shows loading indicator while fetching', () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockReturnValue(new Promise(() => {}));
    vi.spyOn(dqApi, 'listDataQualityFindings').mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('dq-loading')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Successful render
// ---------------------------------------------------------------------------

describe('DataQualityPage — data loaded', () => {
  beforeEach(() => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(makeSummary());
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun());
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue(makeFindings(2));
  });
  afterEach(() => vi.restoreAllMocks());

  it('renders dashboard after load', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-dashboard')).toBeTruthy());
  });

  it('shows run summary card', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-run-summary-card')).toBeTruthy());
  });

  it('shows quality score badge', async () => {
    renderPage();
    await waitFor(() => {
      const badge = screen.getByTestId('dq-quality-score-badge');
      expect(badge.textContent).toContain('87.5');
    });
  });

  it('shows total findings', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('dq-total-findings').textContent).toBe('4');
    });
  });

  it('shows total runs', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('dq-total-runs').textContent).toBe('3');
    });
  });

  it('shows severity breakdown', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-severity-breakdown')).toBeTruthy());
    expect(screen.getByTestId('dq-severity-count-error').textContent).toBe('1');
    expect(screen.getByTestId('dq-severity-count-warning').textContent).toBe('3');
  });

  it('shows type breakdown', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-type-breakdown')).toBeTruthy());
    expect(screen.getByTestId('dq-type-count-DUPLICATE_DOCUMENT').textContent).toBe('2');
    expect(screen.getByTestId('dq-type-count-INVALID_LIFECYCLE').textContent).toBe('2');
  });

  it('renders findings table rows', async () => {
    renderPage();
    await waitFor(() => {
      const rows = screen.getAllByTestId('dq-finding-row');
      expect(rows.length).toBe(2);
    });
  });

  it('shows finding severity in each row', async () => {
    renderPage();
    await waitFor(() => {
      const severityCells = screen.getAllByTestId('dq-finding-severity');
      expect(severityCells.length).toBe(2);
      severityCells.forEach((cell) => expect(cell.textContent).toBe('Warnung'));
    });
  });

  it('shows finding type in each row', async () => {
    renderPage();
    await waitFor(() => {
      const typeCells = screen.getAllByTestId('dq-finding-type');
      typeCells.forEach((cell) => expect(cell.textContent).toBe('DUPLICATE_DOCUMENT'));
    });
  });

  it('shows remediation text in each row', async () => {
    renderPage();
    await waitFor(() => {
      const remCells = screen.getAllByTestId('dq-finding-remediation');
      remCells.forEach((cell) =>
        expect(cell.textContent).toContain('prüfen'),
      );
    });
  });
});

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

describe('DataQualityPage — empty', () => {
  it('shows empty message when no findings', async () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(
      makeSummary({ total_findings: 0, findings_by_severity: {}, findings_by_type: {} }),
    );
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun({ total_findings: 0 }));
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue(makeFindings(0));
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-findings-empty')).toBeTruthy());
    vi.restoreAllMocks();
  });

  it('shows empty breakdown when no findings by severity', async () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(
      makeSummary({ findings_by_severity: {}, findings_by_type: {} }),
    );
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun());
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue(makeFindings(0));
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-severity-empty')).toBeTruthy());
    vi.restoreAllMocks();
  });
});

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

describe('DataQualityPage — error', () => {
  it('shows error state when API fails', async () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockRejectedValue(
      Object.assign(new Error('Server error'), { code: 'SERVER_ERROR', status: 500 }),
    );
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue(makeFindings(0));
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-error')).toBeTruthy());
    vi.restoreAllMocks();
  });
});

// ---------------------------------------------------------------------------
// No repair buttons
// ---------------------------------------------------------------------------

describe('DataQualityPage — read-only', () => {
  beforeEach(() => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(makeSummary());
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun());
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue(makeFindings(2));
  });
  afterEach(() => vi.restoreAllMocks());

  it('has no repair buttons', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('dq-dashboard'));
    const buttons = screen.queryAllByRole('button');
    const repairButtons = buttons.filter((b) =>
      /repair|reparier|fix|beheben|löschen|delete|merge/i.test(b.textContent),
    );
    expect(repairButtons).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Filter interaction
// ---------------------------------------------------------------------------

describe('DataQualityPage — filters', () => {
  it('calls API with severity filter when changed', async () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(makeSummary());
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun());
    const findingsSpy = vi
      .spyOn(dqApi, 'listDataQualityFindings')
      .mockResolvedValue(makeFindings(1));
    renderPage();
    await waitFor(() => screen.getByTestId('dq-findings-filters'));

    fireEvent.change(screen.getByTestId('dq-filter-severity'), { target: { value: 'error' } });

    await waitFor(() => {
      const calls = findingsSpy.mock.calls;
      const lastCall = calls[calls.length - 1][0];
      expect(lastCall?.severity).toBe('error');
    });
    vi.restoreAllMocks();
  });
});

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

describe('DataQualityPage — pagination', () => {
  it('shows pagination when total > pageSize', async () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(makeSummary({ total_findings: 60 }));
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun());
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue({
      items: makeFindings(50).items,
      total: 60,
      limit: 50,
      offset: 0,
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dq-findings-pagination')).toBeTruthy());
    vi.restoreAllMocks();
  });

  it('does not show pagination when total <= pageSize', async () => {
    vi.spyOn(dqApi, 'getDataQualitySummary').mockResolvedValue(makeSummary());
    vi.spyOn(dqApi, 'getDataQualityRun').mockResolvedValue(makeRun());
    vi.spyOn(dqApi, 'listDataQualityFindings').mockResolvedValue(makeFindings(2));
    renderPage();
    await waitFor(() => screen.getByTestId('dq-dashboard'));
    expect(screen.queryByTestId('dq-findings-pagination')).toBeNull();
    vi.restoreAllMocks();
  });
});
