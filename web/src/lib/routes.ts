const NEXT_PATH_KEY = 'oura_coach_next_path';

function normalizeNextPath(path: string | null): string | null {
  if (!path) return null;
  if (!path.startsWith('/')) return null;
  if (path.startsWith('//')) return null;
  return path;
}

export function setNextPath(path: string): void {
  const normalized = normalizeNextPath(path);
  if (!normalized) return;
  try {
    sessionStorage.setItem(NEXT_PATH_KEY, normalized);
  } catch {
    // Ignore storage failures
  }
}

export function getNextPath(): string | null {
  try {
    return normalizeNextPath(sessionStorage.getItem(NEXT_PATH_KEY));
  } catch {
    return null;
  }
}

export function clearNextPath(): void {
  try {
    sessionStorage.removeItem(NEXT_PATH_KEY);
  } catch {
    // Ignore storage failures
  }
}

export function readNextFromQuery(value: string | null): string | null {
  return normalizeNextPath(value);
}
