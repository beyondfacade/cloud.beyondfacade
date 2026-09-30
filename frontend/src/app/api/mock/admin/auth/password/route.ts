import { adminError, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { recordAudit } from "../../security/audit/store";
import { weakPassword } from "../../users/guard";
import { accounts, syncSessionCount } from "../../users/store";

/** mock에서는 현재 비밀번호 "wrong"만 틀린 것으로 본다 (로그인 mock과 같은 규칙). */
export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const body = await request.json().catch(() => null);
  if (typeof body?.current_password !== "string" || body.current_password === "wrong") {
    return adminError(400, "WRONG_PASSWORD", "현재 비밀번호가 올바르지 않습니다.");
  }
  const weak = weakPassword(body?.new_password);
  if (weak) return weak;
  const account = accounts.get(me.username);
  if (account) {
    account.sessions = account.sessions.slice(0, 1);
    syncSessionCount(account);
  }
  recordAudit(me, "password.change", me.username);
  return new Response(null, { status: 204 });
}
