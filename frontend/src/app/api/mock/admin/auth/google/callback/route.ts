import { sessionCookie } from "../../../../admin-fixtures";
import { accounts } from "../../../users/store";
import { oauthCookie, readOauthCookie, redirect } from "../oauth";

const MOCK_GOOGLE_USERNAME = "google.user";

/** 실 API처럼 처음 들어온 구글 계정은 일반 등급으로 만들고, 이후에는 같은 계정으로 로그인한다. */
function mockGoogleAccount(): string {
  if (!accounts.has(MOCK_GOOGLE_USERNAME)) {
    const now = new Date().toISOString();
    accounts.set(MOCK_GOOGLE_USERNAME, {
      user: {
        username: MOCK_GOOGLE_USERNAME, role: "viewer", is_active: true, created_at: now, last_login_at: now,
        active_sessions: 0, email: "google.user@gmail.com", has_password: false, has_google: true,
      },
      sessions: [],
    });
  }
  return MOCK_GOOGLE_USERNAME;
}

/** 실 API처럼 실패는 /login?error=CODE, 성공은 세션 쿠키를 심고 next로 보낸다. */
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const handshake = readOauthCookie(request);
  const clear = oauthCookie(null);
  if (!handshake || params.get("state") !== handshake.state) {
    return redirect("/login?error=OAUTH_STATE_MISMATCH", [clear]);
  }
  if (!params.get("code")) return redirect("/login?error=GOOGLE_LOGIN_FAILED", [clear]);
  return redirect(handshake.next, [clear, sessionCookie(mockGoogleAccount())]);
}
