import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function LoginCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { setAuthFromCallback } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get('token');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        // Redirect to login with error
        navigate(`/login?error=${errorParam}`, { replace: true });
        return;
      }

      if (!token) {
        setError('No authentication token received');
        return;
      }

      try {
        await setAuthFromCallback(token);

        // Get the intended destination from location state, or default to /app
        const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/app';
        navigate(from, { replace: true });
      } catch (err) {
        console.error('Failed to complete login:', err);
        setError(err instanceof Error ? err.message : 'Failed to complete login');
      }
    };

    handleCallback();
  }, [searchParams, navigate, setAuthFromCallback, location.state]);

  if (error) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="bg-surface border border-error/30 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-2">
              Login Failed
            </h2>
            <p className="text-sm text-error mb-4">{error}</p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="px-6 py-2 bg-accent hover:bg-accent-hover text-background font-medium rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="flex items-center gap-3">
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <span className="text-text-secondary">Completing login...</span>
      </div>
    </div>
  );
}
