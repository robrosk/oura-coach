import { Link } from 'react-router-dom';

export function AppHome() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        Welcome to Oura Coach
      </h1>
      <p className="text-text-secondary mb-8">
        Connect your Oura account to get started with personalized wellness
        insights.
      </p>

      {/* Connect card */}
      <div className="bg-surface border border-border rounded-lg p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg
              className="w-6 h-6 text-accent"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold mb-1 text-text-primary">
              Connect Your Oura Ring
            </h2>
            <p className="text-sm text-text-secondary mb-4">
              Authorize Oura Coach to access your sleep, readiness, and activity
              data.
            </p>
            <Link
              to="/app/connect"
              className="inline-block px-6 py-3 bg-accent hover:bg-accent-hover text-background font-semibold rounded-lg transition-colors"
            >
              Connect Oura
            </Link>
          </div>
        </div>
      </div>

      {/* Placeholder features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface-elevated border border-border rounded-lg p-4 opacity-50">
          <h3 className="font-semibold mb-1 text-text-primary">Insights</h3>
          <p className="text-sm text-text-muted">
            Coming soon - Connect Oura first
          </p>
        </div>
        <div className="bg-surface-elevated border border-border rounded-lg p-4 opacity-50">
          <h3 className="font-semibold mb-1 text-text-primary">Experiments</h3>
          <p className="text-sm text-text-muted">
            Coming soon - Connect Oura first
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-8 p-4 bg-surface-elevated rounded-lg border border-border">
        <p className="text-xs text-text-muted">
          <strong className="text-text-secondary">Reminder:</strong> Oura Coach
          provides wellness insights for informational purposes only. It is not
          a medical device and does not provide medical advice, diagnosis, or
          treatment. Always consult a healthcare professional for medical
          concerns.
        </p>
      </div>
    </div>
  );
}
