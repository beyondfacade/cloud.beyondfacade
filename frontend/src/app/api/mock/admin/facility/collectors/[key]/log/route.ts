import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../../../admin-fixtures";
import { COLLECTOR_KEYS, collectorLogFixture } from "../../../../../admin-ops-fixtures";
import { isRunning } from "../../store";

export async function GET(request: Request, { params }: { params: Promise<{ key: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const { key } = await params;
  if (!COLLECTOR_KEYS.has(key)) return adminError(404, "UNKNOWN_COLLECTOR", `모르는 수집기입니다: ${key}`);
  const lines = Math.min(1000, Math.max(10, Number(new URL(request.url).searchParams.get("lines") ?? 200)));
  return Response.json(collectorLogFixture(key, lines, isRunning(key)));
}
