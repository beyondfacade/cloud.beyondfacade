import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../../../admin-fixtures";
import { COLLECTOR_KEYS } from "../../../../../admin-ops-fixtures";
import { recordAudit } from "../../../../security/audit/store";
import { isRunning, markStarted } from "../../store";

export async function POST(request: Request, { params }: { params: Promise<{ key: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const { key } = await params;
  if (!COLLECTOR_KEYS.has(key)) return adminError(404, "UNKNOWN_COLLECTOR", `모르는 수집기입니다: ${key}`);
  if (isRunning(key)) return adminError(409, "COLLECTOR_RUNNING", "수집기가 이미 실행 중입니다.");
  markStarted(key);
  recordAudit(me, "collector.run", key);
  return Response.json({ key, started_at: new Date().toISOString() }, { status: 202 });
}
