import { adminError, mockAdminFrom, sessionCookie, unauthenticated } from "../../../admin-fixtures";
import { recordAudit } from "../../security/audit/store";
import { invalidUsername } from "../../users/guard";
import { accounts } from "../../users/store";

/** 실 API와 같은 계약 — 내 계정명을 바꾸고 AdminMe를 돌려준다. mock 세션 쿠키가 계정명이라 쿠키도 새 이름으로 바꾼다. */
export async function PATCH(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const body = await request.json().catch(() => null);
  const username = typeof body?.username === "string" ? body.username : "";
  const account = accounts.get(me.username)!;
  if (username !== me.username) {
    const invalid = invalidUsername(username);
    if (invalid) return invalid;
    if (accounts.has(username)) return adminError(409, "USERNAME_TAKEN", `이미 있는 계정명입니다: ${username}`);
    accounts.delete(me.username);
    account.user = { ...account.user, username };
    accounts.set(username, account);
    recordAudit(me, "username.change", username, `${me.username} → ${username}`);
  }
  return Response.json(
    { username, role: me.role, can_operate: me.can_operate },
    { headers: { "set-cookie": sessionCookie(username) } },
  );
}
