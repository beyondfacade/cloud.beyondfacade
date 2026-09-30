import { isIP } from "node:net";
import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { ipBlocks } from "./store";

export const runtime = "nodejs";

const FIXED_NOW = Date.parse("2026-09-29T12:00:00+09:00");

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  return Response.json([...ipBlocks.values()]);
}

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const body = await request.json().catch(() => null);
  const ip = typeof body?.ip === "string" ? body.ip.trim() : "";
  if (!isIP(ip)) return adminError(400, "INVALID_IP", `IP 주소 형식이 아닙니다: ${ip}`);
  const ttl = typeof body?.ttl_minutes === "number" ? body.ttl_minutes : null;
  const block = {
    ip,
    reason: (typeof body?.reason === "string" && body.reason.trim()) || "수동 차단",
    created_at: new Date(FIXED_NOW).toISOString(),
    expires_at: ttl ? new Date(FIXED_NOW + ttl * 60_000).toISOString() : null,
    created_by: me.username,
  };
  ipBlocks.set(ip, block);
  return Response.json(block, { status: 201 });
}
