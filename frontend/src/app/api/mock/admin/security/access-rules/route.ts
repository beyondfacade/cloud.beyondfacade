import { isIP } from "node:net";
import type { RulePolicy, RuleTarget } from "@/shared/api/types";
import { adminError, currentDeviceFixture, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../admin-fixtures";
import { recordAudit } from "../audit/store";
import { accessRules } from "./store";

export const runtime = "nodejs";

const FIXED_NOW = Date.parse("2026-09-30T12:00:00+09:00");
const DEVICE_ID = /^[A-Za-z0-9_-]{22}$/;
const MIN_PREFIX: Record<number, number> = { 4: 8, 6: 32 };
const POLICY_LABEL: Record<RulePolicy, string> = { allow: "화이트리스트", deny: "블랙리스트" };

/** 백엔드 IpTarget·DeviceTarget.normalize와 같은 규칙 — 대역 정규화는 호스트 비트 정리 없이 형식만 본다. */
function normalize(target: RuleTarget, raw: string): string | { error: string } {
  const value = raw.trim();
  if (target === "device") return DEVICE_ID.test(value) ? value : { error: "디바이스 ID 형식이 아닙니다 — 이벤트 목록의 22자 ID를 그대로 붙여 넣으세요." };
  const [address, prefix] = value.split("/");
  const version = isIP(address ?? "");
  if (!version || (prefix !== undefined && !/^\d+$/.test(prefix))) return { error: `IP 주소나 대역(CIDR) 형식이 아닙니다: ${raw}` };
  if (prefix !== undefined && Number(prefix) < MIN_PREFIX[version]) return { error: "대역이 너무 넓습니다 — IPv4는 /8, IPv6는 /32보다 좁게 적어 주세요." };
  return value;
}

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  return Response.json(accessRules);
}

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const body = await request.json().catch(() => null);
  const policy = body?.policy as RulePolicy;
  const target = body?.target as RuleTarget;
  if (!["allow", "deny"].includes(policy) || !["ip", "device"].includes(target)) {
    return adminError(400, "INVALID_ACCESS_RULE", `알 수 없는 목록·대상입니다: ${policy} · ${target}`);
  }
  if (policy === "deny" && target === "ip") return adminError(400, "INVALID_ACCESS_RULE", "IP 블랙리스트는 IP 차단 목록에서 추가합니다.");
  const value = normalize(target, typeof body?.value === "string" ? body.value : "");
  if (typeof value !== "string") return adminError(400, "INVALID_ACCESS_RULE", value.error);
  if (policy === "deny" && value === currentDeviceFixture.device_id) {
    return adminError(400, "SELF_BLOCK", "지금 쓰고 있는 내 디바이스는 차단할 수 없습니다.");
  }
  if (accessRules.some((r) => r.policy === policy && r.target === target && r.value === value)) {
    return adminError(409, "ACCESS_RULE_EXISTS", `이미 ${POLICY_LABEL[policy]}에 있습니다: ${value}`);
  }
  const ttl = typeof body?.ttl_minutes === "number" ? body.ttl_minutes : null;
  const rule = {
    id: Math.max(0, ...accessRules.map((r) => r.id)) + 1,
    policy,
    target,
    value,
    note: typeof body?.note === "string" ? body.note.trim() : "",
    created_at: new Date(FIXED_NOW).toISOString(),
    expires_at: ttl ? new Date(FIXED_NOW + ttl * 60_000).toISOString() : null,
    created_by: me.username,
  };
  accessRules.unshift(rule);
  recordAudit(me, "access_rule.create", value, POLICY_LABEL[policy]);
  return Response.json(rule, { status: 201 });
}
