export type RoomKey = "security" | "healthcare" | "facility" | "users";

export interface Room {
  key: RoomKey;
  href: string;
  badge: string;
  title: string;
  titleEn: string;
  subtitle: string;
  /** 스냅샷 폴링 주기(ms) — 설비 지표가 가장 자주 변한다. */
  pollMs: number;
}

export const ROOMS: Room[] = [
  {
    key: "security", href: "/admin/security", badge: "SECURITY AUDIT",
    title: "보안 감사팀", titleEn: "Security Audit",
    subtitle: "관리자 로그인과 접근 이상 징후를 최근 24시간 창으로 감시하고 의심 IP를 차단합니다.",
    pollMs: 15_000,
  },
  {
    key: "healthcare", href: "/admin/healthcare", badge: "AI HEALTHCARE",
    title: "헬스케어실", titleEn: "AI Healthcare",
    subtitle: "LLM 분석 체인과 RAG 검색 파이프라인의 상태·사용량을 진단하고 직접 프로브합니다.",
    pollMs: 30_000,
  },
  {
    key: "facility", href: "/admin/facility", badge: "FACILITY",
    title: "설비실", titleEn: "Facility",
    subtitle: "호스트·GPU·데이터베이스 자원과 수집기별 데이터 신선도를 점검합니다.",
    pollMs: 10_000,
  },
  {
    key: "users", href: "/admin/users", badge: "PEOPLE",
    title: "인사팀", titleEn: "People",
    subtitle: "관리자 계정의 역할과 접속 상태를 관리하고 비밀번호·세션을 정리합니다.",
    pollMs: 30_000,
  },
];

export const ROOM_BY_KEY = Object.fromEntries(ROOMS.map((room) => [room.key, room])) as Record<RoomKey, Room>;

/** 로그인 후 돌아갈 곳 — 외부 URL·프로토콜 상대 경로(//)는 허브로 돌린다(오픈 리다이렉트 방지). */
export function safeAdminNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/admin") || next.startsWith("//") || next.startsWith("/admin/login")) return "/admin";
  return next;
}
