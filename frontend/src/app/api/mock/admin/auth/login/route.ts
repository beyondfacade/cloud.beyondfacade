import { adminError, sessionCookie } from "../../../admin-fixtures";
import { accounts } from "../../users/store";

const INVALID = () => adminError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다.");

function findAccount(loginId: string) {
  if (!loginId.includes("@")) return accounts.get(loginId);
  const email = loginId.toLowerCase();
  return [...accounts.values()].find((account) => account.user.email === email);
}

/**
 * 실 API와 같은 계약 — 성공 시 httpOnly 세션 쿠키 + AdminMe. 아이디 또는 이메일로 mock 회원을 찾고,
 * 비밀번호는 "wrong"만 실패한다. 구글 전용·정지 계정은 실 API처럼 같은 문구로 거절한다.
 */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const loginId = typeof body?.username === "string" ? body.username.trim() : "";
  const password = typeof body?.password === "string" ? body.password : "";
  const account = findAccount(loginId);
  const usable = account?.user.is_active && account.user.has_password;
  if (!account || !usable || !password || password === "wrong") return INVALID();
  const { username, role } = account.user;
  return Response.json(
    { username, role, can_operate: role === "operator" },
    { headers: { "set-cookie": sessionCookie(username) } },
  );
}
