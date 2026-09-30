/** 관리자 mock 픽스처 — 서버 전용. 시각은 고정 ISO 문자열(결정적 데이터). */
import type {
  AdminMe,
  FacilitySnapshot,
  HealthcareSnapshot,
  IpBlock,
  ProbeKind,
  ProbeResult,
  SecurityOverview,
} from "@/shared/api/types";

const SESSION_COOKIE = "metabole_admin";

/** mock 세션 쿠키 값 = 역할. username "viewer"만 조회 관리자다. */
export function mockAdminFrom(request: Request): AdminMe | null {
  const cookie = request.headers.get("cookie") ?? "";
  const value = cookie.split(/;\s*/).find((c) => c.startsWith(`${SESSION_COOKIE}=`))?.split("=")[1];
  if (value !== "viewer" && value !== "operator") return null;
  return { username: value === "viewer" ? "viewer" : "ops", role: value, can_operate: value === "operator" };
}

export function sessionCookie(role: AdminMe["role"] | null): string {
  return role
    ? `${SESSION_COOKIE}=${role}; HttpOnly; Path=/; SameSite=Lax`
    : `${SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0`;
}

export const adminError = (status: number, code: string, message: string) =>
  Response.json({ error: { code, message } }, { status });

export const unauthenticated = () => adminError(401, "UNAUTHENTICATED", "관리자 로그인이 필요합니다.");
export const forbiddenRole = () => adminError(403, "FORBIDDEN_ROLE", "운영 관리자 권한이 필요합니다.");

const ATTACKER = "203.0.113.10";
const SCANNER = "198.51.100.7";

export const securityOverviewFixture: SecurityOverview = {
  generated_at: "2026-09-29T12:00:00+09:00",
  summary: {
    events_24h: 27, failed_logins_24h: 12, scanner_probes_24h: 6, server_errors_24h: 1,
    blocked_requests_24h: 0, open_alerts: 2, blocked_ips: 1,
  },
  alerts: [
    {
      rule: "brute_force_login", severity: "critical", title: "관리자 로그인 실패 12회 (15분)", ip: ATTACKER,
      count: 12, first_seen: "2026-09-29T11:47:10+09:00", last_seen: "2026-09-29T11:58:42+09:00", blocked: false,
    },
    {
      rule: "scanner_probe", severity: "medium", title: "취약점 스캐너 경로 탐색 6회 (1시간)", ip: SCANNER,
      count: 6, first_seen: "2026-09-29T11:05:00+09:00", last_seen: "2026-09-29T11:31:00+09:00", blocked: true,
    },
  ],
  recent_events: [
    { id: 27, occurred_at: "2026-09-29T11:58:42+09:00", kind: "login_failed", ip: ATTACKER, method: "POST", path: "/admin/auth/login", status_code: 401, username: "admin" },
    { id: 26, occurred_at: "2026-09-29T11:52:03+09:00", kind: "login_succeeded", ip: "10.0.0.5", method: "POST", path: "/admin/auth/login", status_code: 200, username: "ops" },
    { id: 25, occurred_at: "2026-09-29T11:31:00+09:00", kind: "scanner_probe", ip: SCANNER, method: "GET", path: "/.env", status_code: 404, username: null },
    { id: 24, occurred_at: "2026-09-29T10:12:44+09:00", kind: "server_error", ip: "10.0.0.5", method: "GET", path: "/regions/1168063000/summary", status_code: 500, username: null },
  ],
};

export const initialIpBlocks: IpBlock[] = [
  { ip: SCANNER, reason: "스캐너 경로 탐색", created_at: "2026-09-29T11:32:00+09:00", expires_at: "2026-09-30T11:32:00+09:00", created_by: "ops" },
];

export const healthcareSnapshotFixture: HealthcareSnapshot = {
  generated_at: "2026-09-29T12:00:00+09:00",
  llm_routes: [
    { role: "primary", provider: "gemini", model: "gemini-2.5-flash", available: true, detail: "API 키 설정됨" },
    { role: "fallback", provider: "ollama", model: "gemma4:12b", available: true, detail: "설치됨" },
  ],
  required_models: [
    { name: "gemma4:12b", purpose: "분석 폴백 LLM", installed: true, loaded: false },
    { name: "qwen3-embedding:4b", purpose: "RAG 검색 임베딩", installed: true, loaded: true },
  ],
  ollama: {
    reachable: true, base_url: "http://127.0.0.1:11434", latency_ms: 4,
    models: [
      { name: "gemma4:12b", size_bytes: 8_100_000_000 },
      { name: "qwen3-embedding:4b", size_bytes: 2_500_000_000 },
    ],
    loaded: ["qwen3-embedding:4b"],
    error: null,
  },
  usage_24h: {
    window_hours: 24, calls: 14, input_tokens: 182_400, output_tokens: 21_300,
    p50_latency_ms: 16_200, p95_latency_ms: 41_800,
    by_model: [
      { model: "gemini-2.5-flash", calls: 12, input_tokens: 160_100, output_tokens: 18_900, avg_latency_ms: 17_400 },
      { model: "gemma4:12b", calls: 2, input_tokens: 22_300, output_tokens: 2_400, avg_latency_ms: 39_900 },
    ],
  },
  usage_7d: {
    window_hours: 168, calls: 61, input_tokens: 801_000, output_tokens: 90_200,
    p50_latency_ms: 17_100, p95_latency_ms: 44_000,
    by_model: [
      { model: "gemini-2.5-flash", calls: 55, input_tokens: 720_000, output_tokens: 82_000, avg_latency_ms: 17_900 },
      { model: "gemma4:12b", calls: 6, input_tokens: 81_000, output_tokens: 8_200, avg_latency_ms: 40_300 },
    ],
  },
  recent_analyses: [
    { id: "a1f0c2", region_code: "1168063000", industry: "academy", model: "gemini-2.5-flash", input_tokens: 13_200, output_tokens: 1_610, latency_ms: 15_800, created_at: "2026-09-29T11:40:00+09:00" },
    { id: "b7e913", region_code: "1144066000", industry: "cafe", model: "gemma4:12b", input_tokens: 11_900, output_tokens: 1_240, latency_ms: 38_100, created_at: "2026-09-29T10:05:00+09:00" },
  ],
  rag: {
    total_chunks: 7_505, embedded_chunks: 7_505,
    by_source: [
      { source_type: "news", chunks: 6_995, embedded: 6_995, latest_published_at: "2026-09-29T11:00:00+09:00" },
      { source_type: "funding", chunks: 510, embedded: 510, latest_published_at: "2026-09-28T09:00:00+09:00" },
    ],
    embedded_by: [{ model: "qwen3-embedding-4b-fp16", chunks: 7_505 }],
  },
};

export function probeFixture(kind: ProbeKind, message: string): ProbeResult {
  const base = { model: null, output: null, input_tokens: null, output_tokens: null, hits: [], error: null };
  if (kind === "llm") {
    return { ...base, kind, ok: true, latency_ms: 1_830, model: "gemini-2.5-flash", output: `(mock) "${message}"에 대한 한 턴 응답입니다.`, input_tokens: 12, output_tokens: 24 };
  }
  return {
    ...base, kind, ok: true, latency_ms: 142,
    hits: [
      { source_type: "news", source_id: "n-1021", score: 0.8123, snippet: "서울시, 소상공인 임대료 지원 확대…", url: "https://example.test/news/1021" },
      { source_type: "funding", source_id: "PBLN_0001", score: 0.7755, snippet: "2026년 소상공인 정책자금 융자사업 공고", url: "https://example.test/funding/1" },
    ],
  };
}

const GB = 1024 ** 3;

export const facilitySnapshotFixture: FacilitySnapshot = {
  generated_at: "2026-09-29T12:00:00+09:00",
  host: {
    hostname: "metabole-dev", platform: "Linux-7.0.0-x86_64", cpu_count: 16, cpu_percent: 23.4,
    load_avg: [2.1, 1.8, 1.6], memory_total_bytes: 64 * GB, memory_available_bytes: 38 * GB,
    swap_total_bytes: 8 * GB, swap_used_bytes: 1 * GB, uptime_seconds: 3 * 86_400 + 5 * 3_600,
    disks: [{ mount: "/", total_bytes: 1_000 * GB, used_bytes: 612 * GB, free_bytes: 388 * GB }],
  },
  gpus: [{ index: 0, name: "NVIDIA GeForce RTX 4090", memory_used_mb: 9_216, memory_total_mb: 24_564, utilization_percent: 12, temperature_c: 46 }],
  services: [
    { name: "postgres", ok: true, latency_ms: 18, detail: "17.2" },
    { name: "ollama", ok: true, latency_ms: 4, detail: "모델 2개 · 로드 1개" },
  ],
  database: {
    version: "17.2", size_bytes: 9 * GB, connections: 7, max_connections: 100,
    alembic_revision: "f4a5b6c7d8e9", pgvector_version: "0.8.0",
    largest_tables: [
      { name: "store", total_bytes: 3 * GB, row_estimate: 1_240_000 },
      { name: "rag_chunk", total_bytes: 1.2 * GB, row_estimate: 7_505 },
      { name: "news_article", total_bytes: 0.4 * GB, row_estimate: 6_995 },
    ],
  },
  collectors: [
    { key: "news-poller", label: "뉴스 폴링", schedule: "매시", status: "ok", last_run_at: "2026-09-29T11:00:05+09:00", table: "news_article", rows: 6_995, latest_data_at: "2026-09-29T10:58:00+09:00" },
    { key: "store-collector", label: "인허가 점포", schedule: "매일 04:20", status: "ok", last_run_at: "2026-09-29T04:27:10+09:00", table: "store", rows: 1_240_000, latest_data_at: "2026-09-28T18:00:00+09:00" },
    { key: "funding-collector", label: "정책자금 공고", schedule: "매일 05:10", status: "late", last_run_at: "2026-09-27T05:10:40+09:00", table: "funding_program", rows: 510, latest_data_at: "2026-09-26T09:00:00+09:00" },
    { key: "interest-rate-collector", label: "금리·임대동향", schedule: "매주 월 05:20", status: "missing", last_run_at: null, table: "interest_rate", rows: 240, latest_data_at: null },
  ],
};
