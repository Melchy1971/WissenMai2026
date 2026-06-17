import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { hasValidatedWorkspace } from '../auth/stateInvariants.js';
import { AppShell } from './AppShell.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';

import { ChatPage } from '../pages/ChatPage.jsx';
import { DashboardPage } from '../pages/DashboardPage.jsx';
import { DataQualityPage } from '../pages/DataQualityPage.jsx';
import { DriftPage } from '../pages/DriftPage.jsx';
import { DriftAnalyticsPage } from '../pages/DriftAnalyticsPage.jsx';
import { DocumentDetailPage } from '../pages/DocumentDetailPage.jsx';
import { DocumentCenterPage } from '../pages/DocumentCenterPage.jsx';
import { ImportCenterPage } from '../pages/ImportCenterPage.jsx';
import { TopicsPage } from '../pages/TopicsPage.jsx';
import { SearchPage } from '../pages/SearchPage.jsx';
import { LoginPage } from '../pages/LoginPage.jsx';
import { RAGCenterPage } from '../pages/RAGCenterPage.jsx';
import { SettingsPage } from '../pages/SettingsPage.jsx';
import { AgentsPage } from '../pages/AgentsPage.jsx';
import { CollaborationPage } from '../pages/CollaborationPage.jsx';
import { GovernancePage } from '../pages/GovernancePage.jsx';
import { SimpleListPage } from '../pages/SimpleListPage.jsx';
import { AdminDiagnosticsPage } from '../pages/AdminDiagnosticsPage.jsx';
import { AnalysisPage } from '../pages/AnalysisPage.jsx';

import { mapError } from '../view-models/mappers.js';

function ProtectedRoute() {
  const location = useLocation();
  const auth = useAuth();
  const { token, isAuthReady, bootstrapError, retryBootstrap } = auth;

  if (!isAuthReady) {
    return <LoadingState label="Authentifizierung wird initialisiert..." />;
  }

  if (!token) {
    return <Navigate replace to="/login" state={{ from: location }} />;
  }

  if (bootstrapError) {
    const mappedError = mapError(bootstrapError);
    return (
      <ErrorState
        error={mappedError}
        testId="auth-error"
        actionLabel={
          bootstrapError.code === 'API_UNREACHABLE' || bootstrapError.code === 'TIMEOUT'
            ? 'Erneut versuchen' : ''}
        onAction={
          bootstrapError.code === 'API_UNREACHABLE' || bootstrapError.code === 'TIMEOUT'
            ? retryBootstrap : null}
      />
    );
  }

  if (!hasValidatedWorkspace(auth, bootstrapError)) {
    return (
      <ErrorState
        error={mapError({
          code: 'WORKSPACE_NOT_CONFIGURED',
          message: 'Geschuetzte Inhalte erfordern einen validierten Workspace.',
          details: {},
          status: 403,
        })}
        testId="auth-error"
      />
    );
  }

  return <AppShell />;
}

/**
 * AdminRoute — SCGB-03 Fix (PRI-6)
 * Schützt Routen, die ausschließlich für Admins zugänglich sind.
 * Voraussetzung: ProtectedRoute muss bereits durchlaufen worden sein (Token + Workspace valid).
 * Prüft zusätzlich auth.user.role === 'admin'. Alle anderen Rollen erhalten 403.
 */
function AdminRoute({ children }) {
  const auth = useAuth();
  const { user } = auth;

  if (!user || user.role !== 'admin') {
    return (
      <ErrorState
        error={{
          code: 'FORBIDDEN',
          title: 'Zugriff verweigert',
          message: 'Dieser Bereich ist ausschliesslich fuer Administratoren zugaenglich.',
          details: {},
          status: 403,
        }}
        testId="admin-access-denied"
      />
    );
  }

  return children;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate replace to="/dashboard" />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:id" element={<ChatPage />} />
        {/* Dokumentenzentrum — neue 3-Panel-Ansicht */}
        <Route path="/documents" element={<DocumentCenterPage />} />
        {/* /documents-legacy kann bei Bedarf auf alte Seite verweisen */}
        <Route path="/import" element={<ImportCenterPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/topics" element={<TopicsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/rag" element={<RAGCenterPage />} />
        <Route path="/data-quality" element={<DataQualityPage />} />
        <Route path="/drift" element={<DriftPage />} />
        <Route path="/drift-analytics/:snapshotType" element={<DriftAnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/tools" element={<SimpleListPage title="Tools" endpoint="/api/v1/tools" testId="tools-page" />} />
        <Route path="/memory" element={<SimpleListPage title="Memory" endpoint="/api/v1/memory" testId="memory-page" />} />
        <Route path="/tasks" element={<SimpleListPage title="Tasks" endpoint="/api/v1/tasks" testId="tasks-page" />} />
        <Route path="/projects" element={<SimpleListPage title="Projects" endpoint="/api/v1/projects" testId="projects-page" />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/collaboration" element={<CollaborationPage />} />
        <Route path="/governance" element={<GovernancePage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/admin/diagnostics" element={<AdminRoute><AdminDiagnosticsPage /></AdminRoute>} />
      </Route>
    </Routes>
  );
}
