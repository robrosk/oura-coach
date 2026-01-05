import { useEffect, useState } from 'react';
import { Link, useParams, Navigate } from 'react-router-dom';
import { getOuraRaw } from '../../lib/api';
import {
  computeStats,
  computeWeeklyTrends,
  getScoreColor,
  getScoreBgColor,
  formatDateShort,
} from '../../lib/oura';
import type { OuraDailyRecord, MetricStats, WeeklyTrend, MetricType } from '../../types';
import { METRIC_CONFIGS } from '../../types';

export function MetricDetail() {
  const { metric } = useParams<{ metric: string }>();
  const [items, setItems] = useState<OuraDailyRecord[]>([]);
  const [stats, setStats] = useState<MetricStats | null>(null);
  const [trends, setTrends] = useState<WeeklyTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Validate metric param
  const isValidMetric = metric && metric in METRIC_CONFIGS;

  useEffect(() => {
    if (!isValidMetric || !metric) return;

    const metricConfig = METRIC_CONFIGS[metric as MetricType];

    async function fetchData() {
      try {
        const response = await getOuraRaw(metricConfig.endpoint, 61);
        const sortedItems = [...response.items].sort((a, b) =>
          b.day.localeCompare(a.day)
        );
        setItems(sortedItems);
        setStats(computeStats(response.items));
        setTrends(computeWeeklyTrends(response.items));
      } catch (err) {
        console.error(`Failed to fetch ${metric}:`, err);
        setError('Failed to load data. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [isValidMetric, metric]);

  // Redirect if invalid metric
  if (!isValidMetric || !metric) {
    return <Navigate to="/app/insights" replace />;
  }

  // Get config after validation
  const config = METRIC_CONFIGS[metric as MetricType];

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        to="/app/insights"
        className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Insights
      </Link>

      {/* Header */}
      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        {config.name} Score
      </h1>
      <p className="text-text-secondary mb-8">{config.description}</p>

      {/* Loading state */}
      {loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-surface border border-border rounded-lg p-4 animate-pulse"
              >
                <div className="h-3 w-12 bg-surface-elevated rounded mb-2" />
                <div className="h-8 w-16 bg-surface-elevated rounded" />
              </div>
            ))}
          </div>
          <div className="bg-surface border border-border rounded-lg p-6 animate-pulse">
            <div className="h-4 w-32 bg-surface-elevated rounded mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-6 bg-surface-elevated rounded" />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="bg-surface border border-error/30 rounded-lg p-6">
          <p className="text-error">{error}</p>
        </div>
      )}

      {/* Data display */}
      {!loading && !error && stats && (
        <div className="space-y-6">
          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-surface border border-border rounded-lg p-4 text-center">
              <p className="text-xs text-text-muted uppercase tracking-wide mb-1">
                Min
              </p>
              <p className={`text-2xl font-bold ${getScoreColor(stats.min)}`}>
                {stats.min}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-lg p-4 text-center">
              <p className="text-xs text-text-muted uppercase tracking-wide mb-1">
                Max
              </p>
              <p className={`text-2xl font-bold ${getScoreColor(stats.max)}`}>
                {stats.max}
              </p>
            </div>
            <div className="bg-surface border border-accent/30 rounded-lg p-4 text-center">
              <p className="text-xs text-text-muted uppercase tracking-wide mb-1">
                Average
              </p>
              <p className={`text-2xl font-bold ${getScoreColor(stats.avg)}`}>
                {stats.avg}
              </p>
            </div>
          </div>

          {/* Weekly trends */}
          {trends.length > 0 && (
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Weekly Trends
              </h2>
              <div className="space-y-3">
                {trends.map((trend) => (
                  <div key={trend.weekStart} className="flex items-center gap-4">
                    <div className="w-28 text-sm text-text-secondary flex-shrink-0">
                      {trend.weekLabel}
                    </div>
                    <div className="flex-1 h-6 bg-surface-elevated rounded-full overflow-hidden">
                      <div
                        className={`h-full ${getScoreBgColor(trend.avg)} rounded-full transition-all`}
                        style={{ width: `${trend.avg}%` }}
                      />
                    </div>
                    <div
                      className={`w-10 text-right text-sm font-semibold ${getScoreColor(trend.avg)}`}
                    >
                      {trend.avg}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All data */}
          {items.length > 0 && (
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                All Data ({items.length} days)
              </h2>
              <div className="max-h-80 overflow-y-auto space-y-2 pr-2">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 py-2 border-b border-border last:border-0"
                  >
                    <div className="w-20 text-sm text-text-secondary flex-shrink-0">
                      {formatDateShort(item.day)}
                    </div>
                    <div className="flex-1 h-4 bg-surface-elevated rounded-full overflow-hidden">
                      <div
                        className={`h-full ${getScoreBgColor(item.score)} rounded-full transition-all`}
                        style={{ width: `${item.score}%` }}
                      />
                    </div>
                    <div
                      className={`w-10 text-right text-sm font-semibold ${getScoreColor(item.score)}`}
                    >
                      {item.score}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No data state */}
          {items.length === 0 && (
            <div className="bg-surface border border-border rounded-lg p-6 text-center">
              <p className="text-text-muted">
                No {config.name.toLowerCase()} data available for the last 60 days.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
