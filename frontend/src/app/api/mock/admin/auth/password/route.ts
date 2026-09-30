import { adminError, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { recordAudit } from "../../security/audit/store";
import { weakPassword } from "../../users/guard";
import { accounts, syncSessionCount } from "../../users/store";

/**
 * mock에서는 현재 비밀번호 "wrong"(또는 빈 값)만 틀린 것으로 본다 (로그인 mock과 같은 규칙).
 * 실 API처럼 비밀번호가 없는 구글 전용 계정은 현재 비밀번호 없이 처음 설정한다.
 */
export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const body = await request.json().catch(() => null);
  const account = accounts.get(me.username);
  const firstTime = account ? !account.user.has_password : false;
  const current = typeof body?.current_password === "string" ? body.current_password : "";
  if (!firstTime && (!current || current === "wrong")) {
    return adminError(400, "WRONG_PASSWORD", "현재 비밀번호가 올바르지 않습니다.");
  }
  const weak = weakPassword(body?.new_password);
  if (weak) return weak;
  if (account) {
    account.user = { ...account.user, has_password: true };
    account.sessions = account.sessions.slice(0, 1);
    syncSessionCount(account);
  }
  recordAudit(me, "password.change", me.username, firstTime ? "처음 설정" : "");
  return new Response(null, { status: 204 });
}
