import { mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { searchMembers } from "../store";

export async function GET(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  return Response.json(searchMembers(me, new URL(request.url).searchParams.get("q") ?? ""));
}
