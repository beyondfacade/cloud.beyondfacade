import type { AdminMe } from "@/shared/api/types";
import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { accounts } from "./store";

const MIN_PASSWORD = 12;

export const weakPassword = (password: unknown) =>
  typeof password !== "string" || password.length < MIN_PASSWORD
    ? adminError(400, "WEAK_PASSWORD", `비밀번호는 ${MIN_PASSWORD}자 이상이어야 합니다.`)
    : null;

/** 남의 계정을 바꾸는 운영 조치 — 실 API 순서(인증 → 권한 → 대상 존재 → 자기 자신)와 같다. */
export async function operatorOnTarget(request: Request, params: Promise<{ username: string }>) {
  const me = mockAdminFrom(request);
  if (!me) return { error: unauthenticated() };
  if (!me.can_operate) return { error: forbiddenRole() };
  const username = decodeURIComponent((await params).username);
  const account = accounts.get(username);
  if (!account) return { error: adminError(404, "ADMIN_USER_NOT_FOUND", `없는 계정입니다: ${username}`) };
  if (username === me.username) {
    return { error: adminError(400, "SELF_CHANGE", "내 계정의 역할·상태·비밀번호는 여기서 바꿀 수 없습니다.") };
  }
  return { me: me as AdminMe, account, username };
}
