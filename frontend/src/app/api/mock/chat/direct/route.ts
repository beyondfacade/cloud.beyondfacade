import { mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { directRoom } from "../store";

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const { user_id } = (await request.json()) as { user_id: number };
  const room = directRoom(me, user_id);
  return room instanceof Response ? room : Response.json(room);
}
