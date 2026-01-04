import { Link } from 'react-router-dom';

export function Welcome() {
  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-8 h-8 text-success"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
          Authorization Complete
        </h1>
        <p className="text-text-secondary">
          If you returned here after authorizing with Oura, your backend should
          have completed the token exchange.
        </p>
      </div>

      {/* Status card */}
      <div className="bg-surface border border-border rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 text-text-primary">
          What happens next?
        </h2>
        <ol className="space-y-4">
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 bg-accent/10 text-accent rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0">
              1
            </span>
            <span className="text-text-secondary">
              The backend securely stores your OAuth tokens
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 bg-accent/10 text-accent rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0">
              2
            </span>
            <span className="text-text-secondary">
              Your Oura data will be fetched when you use the app
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 bg-accent/10 text-accent rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0">
              3
            </span>
            <span className="text-text-secondary">
              Insights and experiments will be generated based on your data
            </span>
          </li>
        </ol>
      </div>

      {/* CTA */}
      <div className="flex flex-col gap-4">
        <Link
          to="/app"
          className="w-full px-6 py-4 bg-accent hover:bg-accent-hover text-background font-semibold rounded-lg transition-colors text-center"
        >
          Go to App Home
        </Link>
      </div>

      {/* Note */}
      <div className="mt-8 p-4 bg-surface-elevated rounded-lg border border-border">
        <p className="text-xs text-text-muted">
          <strong className="text-text-secondary">Note:</strong> This is a
          placeholder page. In the full implementation, the backend will handle
          the OAuth callback and redirect you appropriately based on the
          connection status.
        </p>
      </div>
    </div>
  );
}
