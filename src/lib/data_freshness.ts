/** Daily cron at 02:00 UTC — data older than this is flagged stale on page load. */
export const REFRESH_INTERVAL_MS = 24 * 60 * 60 * 1000;

export type FreshnessStatus = 'fresh' | 'stale' | 'missing';

export interface FreshnessAssessment {
  status: FreshnessStatus;
  ageMs: number | null;
  generatedAt: string | null;
  label: string;
}

export function formatAge(ms: number): string {
  const hours = Math.floor(ms / 3_600_000);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function assessFreshness(
  generatedAt: string | null | undefined,
  now = Date.now(),
): FreshnessAssessment {
  if (!generatedAt) {
    return {
      status: 'missing',
      ageMs: null,
      generatedAt: null,
      label: 'No build timestamp — freshness unknown',
    };
  }
  const ts = Date.parse(generatedAt);
  if (Number.isNaN(ts)) {
    return {
      status: 'missing',
      ageMs: null,
      generatedAt,
      label: 'Invalid build timestamp',
    };
  }
  const ageMs = now - ts;
  const thresholdHours = REFRESH_INTERVAL_MS / 3_600_000;
  if (ageMs > REFRESH_INTERVAL_MS) {
    return {
      status: 'stale',
      ageMs,
      generatedAt,
      label: `Stale — snapshot is ${formatAge(ageMs)} old (>${thresholdHours}h since last pipeline run)`,
    };
  }
  return {
    status: 'fresh',
    ageMs,
    generatedAt,
    label: `Fresh — snapshot ${formatAge(ageMs)} old`,
  };
}
