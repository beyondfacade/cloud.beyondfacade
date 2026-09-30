import { adminError, forbiddenRole, mockAdminFrom, probeFixture, unauthenticated } from "../../../admin-fixtures";

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const body = await request.json().catch(() => null);
  const message = typeof body?.message === "string" ? body.message.trim() : "";
  if ((body?.kind !== "rag" && body?.kind !== "llm") || !message) {
    return adminError(422, "INVALID_PROBE", "kind는 rag 또는 llm, message는 1자 이상이어야 합니다.");
  }
  return Response.json(probeFixture(body.kind, message));
}
