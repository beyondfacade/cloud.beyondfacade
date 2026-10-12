import { mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { roomDenied, sendAttachment } from "../../../store";

/** 본문은 PDF 바이트 그대로, 파일 이름은 ?name= */
export async function POST(request: Request, context: { params: Promise<{ room: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const room = decodeURIComponent((await context.params).room);
  const denied = roomDenied(me, room);
  if (denied) return denied;
  const name = new URL(request.url).searchParams.get("name") ?? "";
  const result = sendAttachment(me, room, name, new Uint8Array(await request.arrayBuffer()));
  return result instanceof Response ? result : Response.json(result, { status: 201 });
}
