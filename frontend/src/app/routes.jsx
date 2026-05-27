import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { hasValidatedWorkspace } from '../auth/stateInvariants.js';
import { AppShell } from './AppShell.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { AdminDiagnosticsPage } from '../pages/AdminDiagnosticsPage.jsx';
import { ChatPage } from '../pages/ChatPage.jsx';
import { DocumentDetailPage } from '../pages/DocumentDetailPage.jsx';
import { DocumentsPage } from '../pages/DocumentsPage.jsx';
import { LoginPage } from '../pages/LoginPage.jsx';
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
        actionLabel={bootstrapError.code === 'API_UNREACHABLE' || bootstrapError.code === 'TIMEOUT' ? 'Erneut versuchen' : ''}
        onAction={bootstrapError.code === 'API_UNREACHABLE' || bootstrapError.code === 'TIMEOUT' ? retryBootstrap : null}
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
        <Route path="/" element={<Navigate replace to="/documents" />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:id" element={<ChatPage />} />
        <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
      </Route>
    </Routes>
  );
}
