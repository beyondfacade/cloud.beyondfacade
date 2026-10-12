import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { messages, roomDenied } from "../../store";

/** 관리자만 — 본문은 지우고 자리만 남긴다. 이미 지운 메시지를 다시 지워도 204. */
export async function DELETE(request: Request, context: { params: Promise<{ id: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const id = Number((await context.params).id);
  const message = messages.find((m) => m.id === id);
  if (!message || roomDenied(me, message.room)) return adminError(404, "CHAT_MESSAGE_NOT_FOUND", "메시지를 찾을 수 없습니다.");
  Object.assign(message, { body: null, deleted: true });
  return new Response(null, { status: 204 });
}
