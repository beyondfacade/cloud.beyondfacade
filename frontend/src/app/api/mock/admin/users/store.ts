import type { AdminSessionInfo, AdminUser } from "@/shared/api/types";

interface MockAccount {
  user: AdminUser;
  sessions: AdminSessionInfo[];
}

const session = (id: string, created: string, ip: string): AdminSessionInfo => ({
  id, created_at: created, expires_at: new Date(Date.parse(created) + 12 * 3_600_000).toISOString(), ip, current: false,
});

/** mock 관리자 계정 — 개발 서버 프로세스 동안만 유지. 로그인 mock의 ops·viewer와 이름을 맞춘다. */
export const accounts = new Map<string, MockAccount>(
  ([
    {
      user: { username: "ops", role: "operator", is_active: true, created_at: "2026-09-20T10:00:00+09:00", last_login_at: "2026-09-29T11:52:03+09:00", active_sessions: 2 },
      sessions: [session("a1b2c3d4e5f6", "2026-09-29T11:52:03+09:00", "10.0.0.5"), session("0f9e8d7c6b5a", "2026-09-29T08:10:00+09:00", "10.0.0.8")],
    },
    {
      user: { username: "viewer", role: "viewer", is_active: true, created_at: "2026-09-21T09:30:00+09:00", last_login_at: "2026-09-29T09:14:40+09:00", active_sessions: 1 },
      sessions: [session("1122aabbccdd", "2026-09-29T09:14:40+09:00", "10.0.0.12")],
    },
    {
      user: { username: "lee.ops", role: "operator", is_active: true, created_at: "2026-09-22T14:00:00+09:00", last_login_at: "2026-09-27T20:01:00+09:00", active_sessions: 0 },
      sessions: [],
    },
    {
      user: { username: "kim.analyst", role: "viewer", is_active: false, created_at: "2026-09-23T11:00:00+09:00", last_login_at: null, active_sessions: 0 },
      sessions: [],
    },
  ] satisfies MockAccount[]).map((account) => [account.user.username, account]),
);

/** mock 로그인 쿠키에는 세션 식별이 없다 — 본인 목록의 첫 세션을 '지금 세션'으로 본다. */
export function sessionsFor(username: string, viewer: string): AdminSessionInfo[] {
  const account = accounts.get(username);
  if (!account) return [];
  return account.sessions.map((s, index) => ({ ...s, current: username === viewer && index === 0 }));
}

export function syncSessionCount(account: MockAccount): void {
  account.user = { ...account.user, active_sessions: account.sessions.length };
}
