import { mockAdminFrom, unauthenticated } from "../../../admin-fixtures";

export async function GET(request: Request) {
  const me = mockAdminFrom(request);
  return me ? Response.json(me) : unauthenticated();
}
