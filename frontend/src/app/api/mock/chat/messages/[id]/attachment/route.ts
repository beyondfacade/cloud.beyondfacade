import { adminError, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { attachments, messages, roomDenied } from "../../../store";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const id = Number((await context.params).id);
  const message = messages.find((m) => m.id === id);
  const content = attachments.get(id);
  if (!message || message.deleted || !content || roomDenied(me, message.room)) {
    return adminError(404, "CHAT_MESSAGE_NOT_FOUND", "파일을 찾을 수 없습니다.");
  }
  return new Response(new Uint8Array(content), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename*=UTF-8''${encodeURIComponent(message.attachment?.name ?? "file.pdf")}`,
    },
  });
}
