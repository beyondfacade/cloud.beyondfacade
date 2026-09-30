import { adminError, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { recordAudit } from "../../../security/audit/store";
import { accounts, sessionsFor, syncSessionCount } from "../../store";

type Context = { params: Promise<{ username: string }> };

/** 본인 또는 운영 관리자만 — 실 API와 같은 판정. */
async function resolve(request: Request, params: Context["params"]) {
  const me = mockAdminFrom(request);
  if (!me) return { error: unauthenticated() };
  const username = decodeURIComponent((await params).username);
  const account = accounts.get(username);
  if (!account) return { error: adminError(404, "ADMIN_USER_NOT_FOUND", `없는 계정입니다: ${username}`) };
  if (username !== me.username && !me.can_operate) {
    return { error: adminError(403, "FORBIDDEN_ROLE", "다른 계정의 세션은 운영 관리자만 볼 수 있습니다.") };
  }
  return { me, account, username };
}

export async function GET(request: Request, { params }: Context) {
  const target = await resolve(request, params);
  if ("error" in target) return target.error;
  return Response.json({ items: sessionsFor(target.username, target.me.username) });
}

export async function DELETE(request: Request, { params }: Context) {
  const target = await resolve(request, params);
  if ("error" in target) return target.error;
  const self = target.username === target.me.username;
  const before = target.account.sessions.length;
  target.account.sessions = self ? target.account.sessions.slice(0, 1) : [];
  syncSessionCount(target.account);
  const revoked = before - target.account.sessions.length;
  recordAudit(target.me, "user.sessions_revoke", target.username, `${revoked}개`);
  return Response.json({ revoked });
}
