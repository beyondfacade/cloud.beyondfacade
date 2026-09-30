import type { AccessEventKind, AdminRole, AlertSeverity, AuditAction, CollectorStatus } from "@/shared/api/types";

export type Tone = "ok" | "warn" | "danger" | "neutral";

const DASH = "—";
const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB"];

/** 1024진법 — 100 이상은 정수, 미만은 소수 한 자리. */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return DASH;
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < BYTE_UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  if (unit === 0) return `${value} B`;
  return `${value >= 100 ? value.toFixed(0) : value.toFixed(1)} ${BYTE_UNITS[unit]}`;
}

/** 가동 시간 — 큰 단위 두 개까지만. */
export function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null) return DASH;
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return `${days}일 ${hours}시간`;
  if (hours > 0) return `${hours}시간 ${minutes}분`;
  return `${minutes}분`;
}

export function formatRelative(iso: string | null | undefined, now: number): string {
  if (!iso) return "기록 없음";
  const diff = Math.max(0, now - Date.parse(iso));
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "방금";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

export function formatMs(ms: number | null | undefined): string {
  if (ms == null) return DASH;
  return ms < 1_000 ? `${Math.round(ms)}ms` : `${(ms / 1_000).toFixed(1)}s`;
}

export function formatCount(value: number | null | undefined): string {
  return value == null ? DASH : value.toLocaleString("ko-KR");
}

export function percentOf(part: number | null | undefined, whole: number | null | undefined): number | null {
  if (part == null || !whole) return null;
  return Math.round((part / whole) * 1_000) / 10;
}

/** 사용률 경보 — 80% 이상 주의, 90% 이상 위험. */
export function usageTone(percent: number | null): Tone {
  if (percent == null) return "neutral";
  if (percent >= 90) return "danger";
  if (percent >= 80) return "warn";
  return "ok";
}

const SEOUL_DATETIME = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
});
const SEOUL_CLOCK = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
});

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? SEOUL_DATETIME.format(new Date(iso)) : DASH;
}

export function formatClock(epochMs: number): string {
  return SEOUL_CLOCK.format(new Date(epochMs));
}

const SEOUL_HOUR_MINUTE = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false,
});
const SEOUL_MONTH_DAY = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit" });

/** 차트 축 눈금 — 하루 이하 창은 시:분, 그보다 길면 월.일. */
export function formatAxisTime(iso: string, windowHours: number): string {
  return (windowHours <= 24 ? SEOUL_HOUR_MINUTE : SEOUL_MONTH_DAY).format(new Date(iso));
}

/** 0~1 비율 → 백분율 한 자리. */
export function formatRate(rate: number | null | undefined): string {
  return rate == null ? DASH : `${Math.round(rate * 1_000) / 10}%`;
}

/** 오류율·폴백률 경보 — 5% 이상 주의, 20% 이상 위험. */
export function rateTone(rate: number | null | undefined): Tone {
  if (rate == null) return "neutral";
  if (rate >= 0.2) return "danger";
  if (rate >= 0.05) return "warn";
  return "ok";
}

export const SEVERITY: Record<AlertSeverity, { label: string; tone: Tone }> = {
  critical: { label: "심각", tone: "danger" },
  high: { label: "높음", tone: "danger" },
  medium: { label: "보통", tone: "warn" },
  low: { label: "낮음", tone: "neutral" },
};

export const EVENT_KIND: Record<AccessEventKind, { label: string; tone: Tone }> = {
  login_failed: { label: "로그인 실패", tone: "warn" },
  login_succeeded: { label: "로그인 성공", tone: "ok" },
  login_throttled: { label: "로그인 제한", tone: "danger" },
  scanner_probe: { label: "스캐너 탐색", tone: "warn" },
  server_error: { label: "서버 오류", tone: "danger" },
  blocked_request: { label: "차단 요청", tone: "neutral" },
};

export const COLLECTOR_STATUS: Record<CollectorStatus, { label: string; tone: Tone }> = {
  ok: { label: "정상", tone: "ok" },
  late: { label: "지연", tone: "warn" },
  missing: { label: "기록 없음", tone: "danger" },
};

export const ROLE: Record<AdminRole, { label: string; tone: Tone }> = {
  viewer: { label: "조회", tone: "neutral" },
  operator: { label: "운영", tone: "ok" },
};

export const AUDIT_ACTION: Record<AuditAction, { label: string; tone: Tone }> = {
  "ip_block.create": { label: "IP 차단", tone: "warn" },
  "ip_block.delete": { label: "차단 해제", tone: "neutral" },
  "probe.run": { label: "프로브 실행", tone: "neutral" },
  "collector.run": { label: "수집기 실행", tone: "neutral" },
  "user.create": { label: "계정 생성", tone: "ok" },
  "user.role": { label: "역할 변경", tone: "warn" },
  "user.suspend": { label: "접속 정지", tone: "danger" },
  "user.reactivate": { label: "정지 해제", tone: "ok" },
  "user.password_reset": { label: "비밀번호 재설정", tone: "warn" },
  "user.sessions_revoke": { label: "세션 종료", tone: "warn" },
  "password.change": { label: "내 비밀번호 변경", tone: "neutral" },
};

/** 보안 이벤트 검색 기간 — 백엔드 보존 기간(90일) 안. */
export const EVENT_WINDOWS: { label: string; hours: number }[] = [
  { label: "24시간", hours: 24 },
  { label: "7일", hours: 168 },
  { label: "30일", hours: 720 },
];

/** 설비 추세 창 — 표본은 8일 보존. */
export const TREND_WINDOWS: { label: string; hours: number }[] = [
  { label: "1시간", hours: 1 },
  { label: "6시간", hours: 6 },
  { label: "24시간", hours: 24 },
  { label: "7일", hours: 168 },
];

/** 차단 기간 선택지 — null은 무기한. 백엔드 허용 범위 1~43200분. */
export const BLOCK_TTL_OPTIONS: { label: string; minutes: number | null }[] = [
  { label: "1시간", minutes: 60 },
  { label: "24시간", minutes: 1_440 },
  { label: "7일", minutes: 10_080 },
  { label: "무기한", minutes: null },
];
