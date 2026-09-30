import { adminError, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { hostHistoryFixture } from "../../../admin-ops-fixtures";

const ALLOWED = new Set([1, 6, 24, 168]);

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const hours = Number(new URL(request.url).searchParams.get("hours") ?? 24);
  if (!ALLOWED.has(hours)) return adminError(422, "VALIDATION_ERROR", "hours는 1·6·24·168 중 하나입니다.");
  return Response.json(hostHistoryFixture(hours));
}
