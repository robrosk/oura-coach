import { ReactNode, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { setNextPath } from '../lib/routes';

interface AuthGateProps {
  children: ReactNode;
}

/**
 * AuthGate protects routes that require authentication.
 * Redirects to /login if user is not authenticated.
 * Preserves the intended destination for redirect after login.
 */
export function AuthGate({ children }: AuthGateProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const nextPath = `${location.pathname}${location.search}`;

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      setNextPath(nextPath);
    }
  }, [isLoading, isAuthenticated, nextPath]);

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-text-secondary">Loading...</span>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Preserve the intended destination
    const nextQuery = encodeURIComponent(nextPath);
    return <Navigate to={`/login?next=${nextQuery}`} replace />;
  }

  return <>{children}</>;
}
