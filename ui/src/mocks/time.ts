// Mock timestamps are relative to page load so cache labels stay realistic.
const loadedAt = Date.now();

export function minutesAgo(minutes: number): string {
  return new Date(loadedAt - minutes * 60_000).toISOString();
}

export const today: string = new Date(loadedAt).toISOString().slice(0, 10);
