import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function Login() {
  const { login, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();

  // Get error from URL params (from OAuth callback)
  const urlParams = new URLSearchParams(location.search);
  const urlError = urlParams.get('error');

  // If already authenticated, show redirect message
  if (isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-secondary mb-4">You are already logged in.</p>
          <Link
            to="/app"
            className="text-accent hover:text-accent-hover transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await login();
      // Will redirect to Google
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start login');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Logo and title */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            <span className="text-accent">O</span>ura Coach
          </h1>
          <p className="text-text-secondary">
            Sign in to access your personalized wellness insights
          </p>
        </div>

        {/* Login card */}
        <div className="bg-surface border border-border rounded-lg p-8">
          {/* Error display */}
          {(error || urlError) && (
            <div className="mb-6 p-4 bg-error/10 border border-error/30 rounded-lg">
              <p className="text-sm text-error">
                {error || getErrorMessage(urlError)}
              </p>
            </div>
          )}

          {/* Google Sign In button */}
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-4 px-6 py-4 bg-white hover:bg-gray-50 text-gray-800 text-lg font-medium rounded-lg border border-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="w-6 h-6 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                <span>Redirecting...</span>
              </>
            ) : (
              <>
                {/* Google Logo */}
                <svg className="w-7 h-7" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <span>Sign in with Google</span>
              </>
            )}
          </button>

          {/* Divider */}
          <div className="my-6 flex items-center">
            <div className="flex-1 border-t border-border" />
            <span className="px-4 text-xs text-text-muted uppercase">
              Secure Authentication
            </span>
            <div className="flex-1 border-t border-border" />
          </div>

          {/* Info */}
          <p className="text-xs text-text-muted text-center">
            By signing in, you agree to our{' '}
            <Link to="/terms" className="text-accent hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link to="/privacy" className="text-accent hover:underline">
              Privacy Policy
            </Link>
            .
          </p>
        </div>

        {/* Back to home */}
        <div className="mt-6 text-center">
          <Link
            to="/"
            className="text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}

function getErrorMessage(error: string | null): string {
  switch (error) {
    case 'access_denied':
      return 'Access was denied. Please try again.';
    case 'invalid_state':
      return 'Invalid session. Please try again.';
    case 'token_exchange_failed':
      return 'Authentication failed. Please try again.';
    case 'userinfo_failed':
      return 'Failed to get user information. Please try again.';
    case 'no_email':
      return 'Could not get email from Google. Please try with a different account.';
    case 'user_not_found':
      return 'User session expired. Please try again.';
    case 'callback_failed':
      return 'Authentication callback failed. Please try again.';
    default:
      return error || 'An unknown error occurred.';
  }
}
