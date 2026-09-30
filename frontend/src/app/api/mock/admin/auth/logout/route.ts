import { sessionCookie } from "../../../admin-fixtures";

export async function POST() {
  return new Response(null, { status: 204, headers: { "set-cookie": sessionCookie(null) } });
}
