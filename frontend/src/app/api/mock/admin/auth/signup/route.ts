import type { AdminUser } from "@/shared/api/types";
import { adminError, sessionCookie } from "../../../admin-fixtures";
import { invalidUsername, weakPassword } from "../../users/guard";
import { accounts } from "../../users/store";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** 실 API와 같은 계약 — 201 + httpOnly 세션 쿠키 + 일반(viewer). 가입한 계정은 mock 인사팀 목록에도 들어간다. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const username = typeof body?.username === "string" ? body.username : "";
  const email = typeof body?.email === "string" ? body.email.trim().toLowerCase() : "";
  const invalid = invalidUsername(username);
  if (invalid) return invalid;
  if (!EMAIL.test(email)) return adminError(400, "INVALID_EMAIL", "이메일 형식이 올바르지 않습니다.");
  const weak = weakPassword(body?.password);
  if (weak) return weak;
  if (accounts.has(username)) return adminError(409, "USERNAME_TAKEN", `이미 있는 계정명입니다: ${username}`);
  if ([...accounts.values()].some((account) => account.user.email === email)) {
    return adminError(409, "EMAIL_TAKEN", "이미 가입된 이메일입니다.");
  }
  const now = new Date().toISOString();
  const user: AdminUser = {
    username, role: "viewer", is_active: true, created_at: now, last_login_at: now, active_sessions: 0,
    email, has_password: true, has_google: false,
  };
  accounts.set(username, { user, sessions: [] });
  return Response.json(
    { username, role: "viewer", can_operate: false },
    { status: 201, headers: { "set-cookie": sessionCookie(username) } },
  );
}
