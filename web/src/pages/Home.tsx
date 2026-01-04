import { Link } from 'react-router-dom';

export function Home() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
      <div className="max-w-xl text-center">
        {/* Logo / App name */}
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          <span className="text-accent">Oura</span> Coach
        </h1>

        {/* Tagline */}
        <p className="text-lg md:text-xl text-text-secondary mb-2">
          Oura-powered wellness insights & experiments.
        </p>
        <p className="text-sm text-text-muted mb-8">Not medical advice.</p>

        {/* Beta badge */}
        <div className="inline-block bg-surface-elevated px-3 py-1 rounded-full text-xs text-accent border border-accent/30 mb-8">
          Beta
        </div>

        {/* Main CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
          <Link
            to="/app"
            className="w-full sm:w-auto px-8 py-4 bg-accent hover:bg-accent-hover text-background font-semibold rounded-lg transition-colors text-center"
          >
            Enter App
          </Link>
        </div>

        {/* Secondary links */}
        <div className="flex items-center justify-center gap-6 text-sm">
          <Link
            to="/privacy"
            className="text-text-secondary hover:text-accent transition-colors"
          >
            Privacy Policy
          </Link>
          <span className="text-border">|</span>
          <Link
            to="/terms"
            className="text-text-secondary hover:text-accent transition-colors"
          >
            Terms of Service
          </Link>
        </div>
      </div>

      {/* Feature highlights (optional) */}
      <div className="max-w-3xl mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 px-4">
        <div className="bg-surface p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-2 text-text-primary">
            View Insights
          </h3>
          <p className="text-sm text-text-secondary">
            Explore your sleep, readiness, and activity data in one place.
          </p>
        </div>
        <div className="bg-surface p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-2 text-text-primary">
            Run Experiments
          </h3>
          <p className="text-sm text-text-secondary">
            Test hypotheses about what affects your wellness metrics.
          </p>
        </div>
        <div className="bg-surface p-6 rounded-lg border border-border">
          <h3 className="text-lg font-semibold mb-2 text-text-primary">
            Track Context
          </h3>
          <p className="text-sm text-text-secondary">
            Log caffeine, alcohol, workouts, and other factors.
          </p>
        </div>
      </div>
    </div>
  );
}
