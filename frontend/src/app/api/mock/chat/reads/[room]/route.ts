import { mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { memberId, reads, roomDenied } from "../../store";

/** 읽음 표시는 앞으로만 간다 — 더 작은 값이 와도 저장된 값을 돌려준다. */
export async function PUT(request: Request, context: { params: Promise<{ room: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const room = decodeURIComponent((await context.params).room);
  const denied = roomDenied(me, room);
  if (denied) return denied;
  const { last_read_id } = (await request.json()) as { last_read_id: number };
  const key = `${memberId(me.username)}:${room}`;
  const stored = Math.max(reads.get(key) ?? 0, last_read_id, 0);
  reads.set(key, stored);
  return Response.json({ room, last_read_id: stored });
}
