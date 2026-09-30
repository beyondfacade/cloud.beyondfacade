const RUN_MS = 8_000;

/** mock 수동 실행 — 시작 후 8초 동안 '실행 중'으로 보인다. 개발 서버 프로세스 동안만 유지. */
const startedAt = new Map<string, number>();

export function isRunning(key: string, now = Date.now()): boolean {
  const started = startedAt.get(key);
  return started !== undefined && now - started < RUN_MS;
}

export function markStarted(key: string, now = Date.now()): void {
  startedAt.set(key, now);
}
