import { adminError, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { searchSecurityEvents } from "../../../admin-ops-fixtures";

const KINDS = new Set(["login_failed", "login_succeeded", "login_throttled", "scanner_probe", "server_error", "blocked_request"]);

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const params = new URL(request.url).searchParams;
  const kind = params.get("kind");
  if (kind && !KINDS.has(kind)) return adminError(422, "VALIDATION_ERROR", `모르는 이벤트 종류: ${kind}`);
  const hours = Number(params.get("hours") ?? 24);
  const limit = Math.min(200, Number(params.get("limit") ?? 50));
  const beforeId = params.get("before_id") ? Number(params.get("before_id")) : null;
  return Response.json(searchSecurityEvents(kind, params.get("ip")?.trim() || null, hours, beforeId, limit));
}
