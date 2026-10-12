import { adminError, mockAdminFrom, mockMe, unauthenticated } from "../../../admin-fixtures";
import { accounts } from "../../users/store";

/** 실 API와 같은 계약 — 전문가만, 앞뒤 공백을 떼고 1~20자, null은 비운다. 응답은 AdminMe. */
export async function PATCH(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (me.role !== "expert") return adminError(403, "FORBIDDEN_ROLE", "전문가 계정만 전문 업종을 정할 수 있습니다.");
  const body = await request.json().catch(() => null);
  const specialty = typeof body?.specialty === "string" ? body.specialty.trim() : null;
  if (specialty !== null && (specialty.length < 1 || specialty.length > 20)) {
    return adminError(400, "INVALID_SPECIALTY", "전문 업종은 1~20자여야 합니다.");
  }
  accounts.get(me.username)!.specialty = specialty;
  return Response.json(mockMe(me.username));
}
