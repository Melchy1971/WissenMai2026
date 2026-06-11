import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { hasValidatedWorkspace } from '../auth/stateInvariants.js';
import { AppShell } from './AppShell.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';

// Existing pages
import { AdminDiagnosticsPage } from '../pages/AdminDiagnosticsPage.jsx';
import { DataQualityPage } from '../pages/DataQualityPage.jsx';
import { ChatPage } from '../pages/ChatPage.jsx';
import { DocumentDetailPage } from '../pages/DocumentDetailPage.jsx';
import { DocumentsPage } from '../pages/DocumentsPage.jsx';
import { LoginPage } from '../pages/LoginPage.jsx';

// New pages
import { DashboardPage } from '../pages/DashboardPage.jsx';
import { ToolCenterPage } from '../pages/ToolCenterPage.jsx';
import { MemoryCenterPage } from '../pages/MemoryCenterPage.jsx';
import { TaskCenterPage } from '../pages/TaskCenterPage.jsx';
import { ProjectCenterPage } from '../pages/ProjectCenterPage.jsx';
import { RAGCenterPage } from '../pages/RAGCenterPage.jsx';
import { AgentCenterPage } from '../pages/AgentCenterPage.jsx';
import { CollaborationCenterPage } from '../pages/CollaborationCenterPage.jsx';
import { GovernanceCenterPage } from '../pages/GovernanceCenterPage.jsx';
import { SettingsPage } from '../pages/SettingsPage.jsx';

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

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        {/* Redirect root → dashboard */}
        <Route path="/" element={<Navigate replace to="/dashboard" />} />

        {/* Existing routes */}
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:id" element={<ChatPage />} />
        <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
        <Route path="/data-quality" element={<DataQualityPage />} />

        {/* New routes */}
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/tools" element={<ToolCenterPage />} />
        <Route path="/memory" element={<MemoryCenterPage />} />
        <Route path="/tasks" element={<TaskCenterPage />} />
        <Route path="/projects" element={<ProjectCenterPage />} />
        <Route path="/rag" element={<RAGCenterPage />} />
        <Route path="/agents" element={<AgentCenterPage />} />
        <Route path="/collaboration" element={<CollaborationCenterPage />} />
        <Route path="/governance" element={<GovernanceCenterPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
