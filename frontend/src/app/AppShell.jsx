import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { PrivacyModeBanner } from '../components/shared/PrivacyModeBanner.jsx';
import { getDriftOverview } from '../api/drift_analytics.js';
import { getSystemStatus } from '../api/status.js';

const STATUS_REFRESH_INTERVAL_MS = 30_000;

// ── Telekom logo ──────────────────────────────────────────────────────────────

function TelekomLogo() {
  return (
    <svg className="shell__logo" viewBox="0 0 34 34" fill="none"
      xmlns="http://www.w3.org/2000/svg" aria-label="Deutsche Telekom">
      <rect width="34" height="34" rx="6" fill="#E20074" />
      <path d="M7 10h20v4h-8v10h-4V14H7v-4z" fill="#FFFFFF" />
    </svg>
  );
}

// ── Drift status helpers ──────────────────────────────────────────────────────

const DRIFT_STATUS_PRIORITY = { PASS: 0, WARNING: 1, FAIL: 2, BLOCKED: 3 };

const DRIFT_STATUS_STYLE = {
  PASS:    { bg: '#2e7d32', color: '#fff', label: 'PASS' },
  WARNING: { bg: '#e65100', color: '#fff', label: 'WARN' },
  FAIL:    { bg: '#c62828', color: '#fff', label: 'FAIL' },
  BLOCKED: { bg: '#6a1a6a', color: '#fff', label: 'BLOCKED' },
};

/**
 * Counts how many drift widgets are BLOCKED (for nav badge).
 * Missing data (status=null) counts as WARNING, not BLOCKED.
 */
function countBlocked(overview) {
  if (!overview) return 0;
  const keys = ['product_maturity', 'gold_path', 'release_gate', 'test_coverage', 'id_leak_audit', 'security_audit'];
  return keys.reduce((n, k) => {
    const w = overview[k];
    return n + (w?.status === 'BLOCKED' ? 1 : 0);
  }, 0);
}

// ── Global drift badge (status bar) ──────────────────────────────────────────

function DriftGlobalBadge({ overview }) {
  if (!overview) return null;
  const style = DRIFT_STATUS_STYLE[overview.global_status];
  if (!style) return null;

  return (
    <span
      className="shell__drift-badge"
      style={{ background: style.bg, color: style.color }}
      title={`Drift-Gesamtstatus: ${overview.global_status}`}
    >
      Drift: {style.label}
    </span>
  );
}

// ── Nav badge for BLOCKED count ───────────────────────────────────────────────

function BlockedBadge({ count }) {
  if (!count || count === 0) return null;
  return (
    <span
      className="shell__nav-badge"
      aria-label={`${count} blockiert`}
      title={`${count} Drift-Bereich(e) BLOCKED`}
    >
      {count}
    </span>
  );
}

// ── Navigation config ─────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { to: '/dashboard',   label: 'Dashboard' },
  { to: '/documents',   label: 'Dokumente' },
  { to: '/topics',      label: 'Themen' },
  { to: '/import',      label: 'Import' },
  { to: '/search',      label: 'Suche' },
  { to: '/rag',         label: 'Datenanalyse' },
  { to: '/drift',       label: 'Drift' },
  { to: '/analysis',    label: 'Analysen' },
  { to: '/settings',    label: 'Einstellungen' },
];

// Drift Analytics nav is NOT a separate top-level nav item — it is accessible
// via Dashboard → Drift card click → /drift-analytics/:type.
// The "Drift" nav item here goes to /drift (M5b detection, existing).

// ── AppShell ──────────────────────────────────────────────────────────────────

export function AppShell() {
  const navigate = useNavigate();
  const { token, user, active_workspace_id: workspaceId, memberships, signOut, switchWorkspace } = useAuth();
  const [status, setStatus] = useState(null);
  const [driftOverview, setDriftOverview] = useState(null);

  useEffect(() => {
    let controller = null;
    const refreshStatus = () => {
      controller?.abort();
      controller = new AbortController();
      getSystemStatus({ signal: controller.signal }).then(setStatus).catch((error) => {
        if (error?.name !== 'AbortError') setStatus(null);
      });
    };
    refreshStatus();
    const intervalId = window.setInterval(refreshStatus, STATUS_REFRESH_INTERVAL_MS);
    window.addEventListener('focus', refreshStatus);
    return () => {
      controller?.abort();
      window.clearInterval(intervalId);
      window.removeEventListener('focus', refreshStatus);
    };
  }, [workspaceId]);

  // Load drift overview once on mount — best-effort, no error display in shell
  useEffect(() => {
    getDriftOverview().then(setDriftOverview).catch(() => null);
  }, []);

  async function handleLogout() {
    await signOut();
    navigate('/login', { replace: true });
  }

  const privacyMode = status?.privacy_mode ?? false;
  const provider    = status?.provider_name ?? '—';
  const autonomy    = status?.autonomy_level ?? '—';
  const release     = status?.release_status ?? '—';
  const blockedCount = countBlocked(driftOverview);

  return (
    <div className="shell" data-testid="app-shell">
      <PrivacyModeBanner enabled={privacyMode} />

      {/* Status-Header */}
      <div className="shell__status-bar" data-testid="status-bar">
        <span>Workspace: <strong>{memberships.length > 0 ? 'aktiv' : '—'}</strong></span>
        <span>Provider: <strong>{provider}</strong></span>
        <span>Autonomie: <strong>{autonomy}</strong></span>
        <span>Release: <strong>{release}</strong></span>
        {privacyMode && <span className="badge badge--warning">PRIVACY MODE</span>}
        <DriftGlobalBadge overview={driftOverview} />
      </div>

      <header className="shell__header">
        <div className="shell__brand">
          <TelekomLogo />
          <div className="shell__title-group">
            <p className="shell__eyebrow">Deutsche Telekom</p>
            <span className="shell__app-name">Wissens-DB</span>
          </div>
        </div>

        <nav aria-label="Hauptnavigation">
          <div className="shell__nav">
            {NAV_ITEMS.map(item => {
              // Show BLOCKED count badge on Dashboard nav item when drift has blockers
              const showBadge = item.to === '/dashboard' && blockedCount > 0;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => isActive ? 'nav-link nav-link--active' : 'nav-link'}
                  style={{ position: 'relative' }}
                >
                  {item.label}
                  {showBadge && <BlockedBadge count={blockedCount} />}
                </NavLink>
              );
            })}
          </div>
        </nav>

        <div className="shell__session">
          <div className="shell__session-meta">
            <strong>{token ? (user?.display_name || user?.login || 'Angemeldet') : 'Gast'}</strong>
            {memberships.length > 1 ? (
              <select aria-label="Workspace wechseln" value={workspaceId || ''}
                onChange={e => switchWorkspace(e.target.value)}>
                {memberships.map((m, idx) => (
                  <option key={m.workspace_id} value={m.workspace_id}>{`Workspace ${idx + 1} (${m.role})`}</option>
                ))}
              </select>
            ) : (
              <span>{memberships.length > 0 ? memberships[0].role : 'Kein Workspace'}</span>
            )}
          </div>
          {token && (
            <button type="button" className="button-secondary" onClick={handleLogout}>
              Abmelden
            </button>
          )}
        </div>
      </header>

      <main className="shell__content" data-testid="workspace-ready">
        <Outlet />
      </main>

      <style>{`
        /* Global drift badge in status bar */
        .shell__drift-badge {
          padding: 2px 9px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          margin-left: 4px;
        }

        /* Nav badge (BLOCKED count) */
        .shell__nav-badge {
          position: absolute;
          top: -5px;
          right: -8px;
          background: #6a1a6a;
          color: #fff;
          font-size: 9px;
          font-weight: 700;
          padding: 1px 5px;
          border-radius: 8px;
          line-height: 1.4;
          pointer-events: none;
        }
      `}</style>
    </div>
  );
}
