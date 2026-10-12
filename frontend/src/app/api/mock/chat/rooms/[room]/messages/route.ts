import { mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { messages, PAGE_SIZE, present, roomDenied, send } from "../../../store";

type Context = { params: Promise<{ room: string }> };

const roomKey = async (context: Context) => decodeURIComponent((await context.params).room);

export async function GET(request: Request, context: Context) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const room = await roomKey(context);
  const denied = roomDenied(me, room);
  if (denied) return denied;
  const beforeId = Number(new URL(request.url).searchParams.get("before_id")) || Infinity;
  const older = messages.filter((m) => m.room === room && m.id < beforeId);
  return Response.json({ items: older.slice(-PAGE_SIZE).map(present), has_more: older.length > PAGE_SIZE });
}

export async function POST(request: Request, context: Context) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const room = await roomKey(context);
  const denied = roomDenied(me, room);
  if (denied) return denied;
  const body = (await request.json()) as { body: string; reply_to_id: number | null };
  const result = send(me, room, body.body ?? "", body.reply_to_id ?? null);
  return result instanceof Response ? result : Response.json(result, { status: 201 });
}
