import { mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { auditEntries } from "./store";

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const params = new URL(request.url).searchParams;
  const action = params.get("action");
  const beforeId = params.get("before_id") ? Number(params.get("before_id")) : null;
  const limit = Math.min(200, Number(params.get("limit") ?? 50));
  const matched = auditEntries.filter(
    (entry) => (!action || entry.action === action) && (beforeId === null || (entry.id ?? 0) < beforeId),
  );
  const items = matched.slice(0, limit);
  return Response.json({ items, next_before_id: matched.length > limit ? items[items.length - 1].id : null });
}
