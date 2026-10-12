import { mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { roomsFor } from "../store";

export async function GET(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  return Response.json(roomsFor(me));
}
