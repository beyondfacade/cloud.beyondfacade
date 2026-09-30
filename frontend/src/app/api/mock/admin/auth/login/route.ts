import { adminError, sessionCookie } from "../../../admin-fixtures";

/** 실 API와 같은 계약 — 성공 시 httpOnly 세션 쿠키 + AdminMe. mock에서는 비밀번호 "wrong"만 실패한다. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const username = typeof body?.username === "string" ? body.username.trim() : "";
  const password = typeof body?.password === "string" ? body.password : "";
  if (!username || !password || password === "wrong") {
    return adminError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다.");
  }
  const role = username === "viewer" ? "viewer" : "operator";
  return Response.json(
    { username, role, can_operate: role === "operator" },
    { headers: { "set-cookie": sessionCookie(role) } },
  );
}
