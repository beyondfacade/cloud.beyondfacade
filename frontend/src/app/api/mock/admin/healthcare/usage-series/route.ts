import { adminError, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { usageSeriesFixture } from "../../../admin-ops-fixtures";

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const hours = Number(new URL(request.url).searchParams.get("hours") ?? 24);
  if (hours !== 24 && hours !== 168) return adminError(422, "VALIDATION_ERROR", "hours는 24 또는 168입니다.");
  return Response.json(usageSeriesFixture(hours));
}
