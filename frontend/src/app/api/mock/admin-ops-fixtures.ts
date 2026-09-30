/** 관리자 운영 강화 mock 픽스처 — 보안 이벤트 검색·추세·LLM 시계열·수집기 로그. 서버 전용, 결정적 데이터. */
import type { AccessEvent, AccessEventKind, CollectorLog, HostHistory, HostPoint, UsageSeries } from "@/shared/api/types";

const NOW = Date.parse("2026-09-29T12:00:00+09:00");
const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

const ATTACKER_DEVICE = { device: "Xk3vQ9mZt2LpW8rN1sYb0c", ua: "python-requests/2.32" };
const OPS_DEVICE = { device: "Mo7pL2qR9tVx4nZ8cK1wJd", ua: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140.0 Safari/537.36" };
const NO_DEVICE = { device: null, ua: "curl/8.5.0" };

const EVENT_PATTERN: {
  kind: AccessEventKind; ip: string; method: string; path: string; status: number; username: string | null;
  device: string | null; ua: string;
}[] = [
  { kind: "login_failed", ip: "203.0.113.10", method: "POST", path: "/admin/auth/login", status: 401, username: "admin", ...ATTACKER_DEVICE },
  { kind: "scanner_probe", ip: "198.51.100.7", method: "GET", path: "/.env", status: 404, username: null, ...NO_DEVICE },
  { kind: "login_succeeded", ip: "10.0.0.5", method: "POST", path: "/admin/auth/login", status: 200, username: "ops", ...OPS_DEVICE },
  { kind: "scanner_probe", ip: "198.51.100.7", method: "GET", path: "/wp-login.php", status: 404, username: null, ...NO_DEVICE },
  { kind: "server_error", ip: "10.0.0.5", method: "GET", path: "/regions/1168063000/summary", status: 500, username: null, ...NO_DEVICE },
  { kind: "blocked_request", ip: "198.51.100.7", method: "GET", path: "/admin/security/overview", status: 403, username: null, ...NO_DEVICE },
];

/** 20분 간격 72건(24시간) — id가 클수록 최신. "더 보기" 쪽 나눔을 확인할 만큼 넉넉하게. */
export const securityEventsFixture: AccessEvent[] = Array.from({ length: 72 }, (_, index) => {
  const pattern = EVENT_PATTERN[index % EVENT_PATTERN.length];
  return {
    id: 72 - index,
    occurred_at: new Date(NOW - index * 20 * MINUTE).toISOString(),
    kind: pattern.kind,
    ip: pattern.ip,
    method: pattern.method,
    path: pattern.path,
    status_code: pattern.status,
    username: pattern.username,
    device_id: pattern.device,
    user_agent: pattern.ua,
  };
});

export function searchSecurityEvents(
  kind: string | null, ip: string | null, hours: number, beforeId: number | null, limit: number,
): { items: AccessEvent[]; next_before_id: number | null } {
  const since = NOW - hours * HOUR;
  const matched = securityEventsFixture.filter(
    (event) =>
      (!kind || event.kind === kind) &&
      (!ip || event.ip === ip) &&
      Date.parse(event.occurred_at) >= since &&
      (beforeId === null || (event.id ?? 0) < beforeId),
  );
  const items = matched.slice(0, limit);
  return { items, next_before_id: matched.length > limit ? items[items.length - 1].id : null };
}

const wave = (index: number, base: number, amplitude: number, period: number) =>
  Math.round((base + amplitude * Math.sin((index / period) * Math.PI * 2)) * 10) / 10;

const MAX_POINTS = 240;

export function hostHistoryFixture(hours: number): HostHistory {
  const bucketSeconds = Math.max(60, Math.ceil((hours * 3600) / MAX_POINTS / 60) * 60);
  const count = Math.min(MAX_POINTS, Math.floor((hours * 3600) / bucketSeconds));
  const points: HostPoint[] = Array.from({ length: count }, (_, index) => ({
    t: new Date(NOW - (count - 1 - index) * bucketSeconds * 1000).toISOString(),
    cpu_percent: wave(index, 24, 14, 60),
    load1: wave(index, 2, 1.2, 60),
    memory_percent: wave(index, 41, 6, 120),
    swap_percent: 12.5,
    disk_percent: Math.round((61 + index * 0.002) * 10) / 10,
    gpu_util_percent: index % 45 < 6 ? 88 : wave(index, 9, 5, 30),
    gpu_memory_percent: index % 45 < 6 ? 71.2 : 37.5,
    gpu_temp_c: index % 45 < 6 ? 71 : wave(index, 46, 3, 30),
  }));
  return { generated_at: new Date(NOW).toISOString(), hours, bucket_seconds: bucketSeconds, points };
}

const BUCKET_HOURS: Record<number, number> = { 24: 1, 168: 6 };

export function usageSeriesFixture(hours: 24 | 168): UsageSeries {
  const bucketHours = BUCKET_HOURS[hours];
  const count = hours / bucketHours;
  const points = Array.from({ length: count }, (_, index) => {
    const busy = index % 8 >= 3 && index % 8 <= 5;
    const analyses = busy ? 3 : index % 3 === 0 ? 1 : 0;
    const fallback = busy && index % 16 === 4 ? 1 : 0;
    const error = index === count - 7 ? 1 : 0;
    return {
      start: new Date(NOW - (count - 1 - index) * bucketHours * HOUR).toISOString(),
      analyses,
      tokens: analyses * 18_400,
      ok: analyses,
      fallback,
      error,
    };
  });
  const ok = points.reduce((sum, p) => sum + p.ok, 0);
  const fallback = points.reduce((sum, p) => sum + p.fallback, 0);
  const error = points.reduce((sum, p) => sum + p.error, 0);
  const attempts = ok + fallback + error;
  const rate = (n: number) => (attempts ? Math.round((n / attempts) * 10_000) / 10_000 : null);
  return {
    generated_at: new Date(NOW).toISOString(),
    hours,
    bucket_hours: bucketHours,
    points,
    outcomes: { attempts, ok, fallback, error, fallback_rate: rate(fallback), error_rate: rate(error) },
    by_hour: Array.from({ length: 24 }, (_, hour) => (hour >= 10 && hour <= 17 ? 2 + (hour % 3) : hour >= 20 ? 1 : 0)),
  };
}

export const COLLECTOR_KEYS = new Set([
  "news-poller", "store-collector", "funding-collector", "rag-indexer", "interest-rate-collector",
  "childcare-collector", "convenience-collector", "host-metrics-sampler", "admin-housekeeping",
]);

export function collectorLogFixture(key: string, lines: number, running: boolean): CollectorLog {
  const rows = Array.from({ length: 40 }, (_, index) => {
    const minute = String(index % 60).padStart(2, "0");
    return index === 39
      ? `[2026-09-29 05:10:${minute}] GET https://apis.data.go.kr/x?serviceKey=***&pageNo=4 → 429 재시도`
      : `[2026-09-29 05:10:${minute}] ${key} 처리 ${index * 25}건`;
  });
  return {
    key,
    log_file: `${key}.log`,
    lines: rows.slice(-lines),
    last_run_at: "2026-09-29T05:10:40+09:00",
    running,
  };
}
