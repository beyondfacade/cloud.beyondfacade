import { mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { expertRoom } from "../store";

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const room = expertRoom(me);
  return room instanceof Response ? room : Response.json(room);
}
