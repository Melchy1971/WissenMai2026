import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { AppShell } from './AppShell.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { AdminDiagnosticsPage } from '../pages/AdminDiagnosticsPage.jsx';
import { ChatPage } from '../pages/ChatPage.jsx';
import { DocumentDetailPage } from '../pages/DocumentDetailPage.jsx';
import { DocumentsPage } from '../pages/DocumentsPage.jsx';
import { LoginPage } from '../pages/LoginPage.jsx';

function ProtectedRoute() {
  const location = useLocation();
  const { token, isAuthReady, bootstrapError } = useAuth();

  if (!isAuthReady) {
    return <LoadingState label="Authentifizierung wird initialisiert..." />;
  }

  if (!token) {
    return <Navigate replace to="/login" state={{ from: location }} />;
  }

  if (bootstrapError) {
    return <ErrorState error={bootstrapError} />;
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
