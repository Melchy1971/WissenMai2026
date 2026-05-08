import { AuthProvider } from '../auth/AuthContext.jsx';
import { ErrorBoundary } from '../components/status/ErrorBoundary.jsx';
import { AppRoutes } from './routes.jsx';

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  );
}
