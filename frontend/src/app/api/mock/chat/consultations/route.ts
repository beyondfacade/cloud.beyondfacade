import { mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { buyConsultation } from "../store";

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const { expert_id, hours } = (await request.json()) as { expert_id: number; hours: number };
  const room = buyConsultation(me, expert_id, hours);
  return room instanceof Response ? room : Response.json(room, { status: 201 });
}
