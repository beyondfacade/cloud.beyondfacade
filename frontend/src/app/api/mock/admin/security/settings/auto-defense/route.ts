import type { AutoDefense } from "@/shared/api/types";
import { adminError, autoDefenseFixture, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { recordAudit } from "../../audit/store";

export const runtime = "nodejs";

/** mock 자동 방어 스위치 — 개발 서버 프로세스 동안만 유지된다. */
let state: AutoDefense = { ...autoDefenseFixture };

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  return Response.json(state);
}

export async function PUT(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const body = await request.json().catch(() => null);
  if (typeof body?.enabled !== "boolean") return adminError(422, "VALIDATION_ERROR", "enabled는 true 또는 false여야 합니다.");
  state = { ...state, enabled: body.enabled, updated_at: new Date().toISOString(), updated_by: me.username };
  recordAudit(me, "auto_defense.toggle", "auto_defense", body.enabled ? "켬" : "끔");
  return Response.json(state);
}
