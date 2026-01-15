/**
 * Oura data utilities for computing stats and trends
 */

import type { OuraDailyRecord, MetricStats, WeeklyTrend } from '../types';

/**
 * Compute min, max, and average stats from daily records
 */
export function computeStats(items: OuraDailyRecord[]): MetricStats {
  const scores = items
    .map((item) => item.score)
    .filter((score): score is number => score != null && !isNaN(score));

  if (scores.length === 0) {
    return { min: 0, max: 0, avg: 0, count: 0 };
  }

  return {
    min: Math.min(...scores),
    max: Math.max(...scores),
    avg: Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length),
    count: scores.length,
  };
}

/**
 * Get the Monday of the week for a given date
 */
function getWeekStart(dateStr: string): string {
  const date = parseYmd(dateStr);
  if (!date) return dateStr;
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Sunday
  const monday = new Date(date);
  monday.setDate(diff);
  return formatYmd(monday);
}

/**
 * Format a week range label (e.g., "Dec 30 - Jan 5")
 */
function formatWeekLabel(weekStart: string): string {
  const start = parseYmd(weekStart);
  if (!start) return weekStart;
  const end = new Date(start);
  end.setDate(end.getDate() + 6);

  const startMonth = start.toLocaleDateString('en-US', { month: 'short' });
  const startDay = start.getDate();
  const endMonth = end.toLocaleDateString('en-US', { month: 'short' });
  const endDay = end.getDate();

  if (startMonth === endMonth) {
    return `${startMonth} ${startDay} - ${endDay}`;
  }
  return `${startMonth} ${startDay} - ${endMonth} ${endDay}`;
}

/**
 * Group daily records by week and compute weekly averages
 */
export function computeWeeklyTrends(items: OuraDailyRecord[]): WeeklyTrend[] {
  // Group items by week
  const weekMap = new Map<string, number[]>();

  for (const item of items) {
    if (item.score == null || isNaN(item.score)) continue;

    const weekStart = getWeekStart(item.day);
    const existing = weekMap.get(weekStart) || [];
    existing.push(item.score);
    weekMap.set(weekStart, existing);
  }

  // Convert to array and compute averages
  const trends: WeeklyTrend[] = [];
  for (const [weekStart, scores] of weekMap.entries()) {
    trends.push({
      weekStart,
      weekLabel: formatWeekLabel(weekStart),
      avg: Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length),
      count: scores.length,
    });
  }

  // Sort by week (most recent first)
  trends.sort((a, b) => b.weekStart.localeCompare(a.weekStart));

  return trends;
}

/**
 * Get Tailwind color class based on score value (0-100)
 */
export function getScoreColor(score: number): string {
  if (score >= 85) return 'text-success';
  if (score >= 70) return 'text-accent';
  if (score >= 50) return 'text-warning';
  return 'text-error';
}

/**
 * Get Tailwind background color class based on score value
 */
export function getScoreBgColor(score: number): string {
  if (score >= 85) return 'bg-success';
  if (score >= 70) return 'bg-accent';
  if (score >= 50) return 'bg-warning';
  return 'bg-error';
}

/**
 * Format a date string for display (e.g., "Jan 4, 2026")
 */
export function formatDate(dateStr: string): string {
  const date = parseYmd(dateStr);
  if (!date) return dateStr;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format a date string for short display (e.g., "Jan 4")
 */
export function formatDateShort(dateStr: string): string {
  const date = parseYmd(dateStr);
  if (!date) return dateStr;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

function parseYmd(dateStr: string): Date | null {
  const parts = dateStr.split('-').map((value) => Number(value));
  if (parts.length !== 3) return null;
  const [year, month, day] = parts;
  if (!year || !month || !day) return null;
  const date = new Date(year, month - 1, day);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function formatYmd(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
