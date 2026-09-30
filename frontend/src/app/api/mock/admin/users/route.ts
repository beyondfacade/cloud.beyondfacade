import type { AdminUser } from "@/shared/api/types";
import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { recordAudit } from "../security/audit/store";
import { weakPassword } from "./guard";
import { accounts } from "./store";

const USERNAME = /^[a-z0-9][a-z0-9._-]{2,31}$/;

const STATUS_FILTERS: Record<string, (user: AdminUser) => boolean> = {
  all: () => true,
  active: (user) => user.is_active,
  suspended: (user) => !user.is_active,
};

export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const params = new URL(request.url).searchParams;
  const q = (params.get("q") ?? "").trim().toLowerCase();
  const role = params.get("role");
  const keep = STATUS_FILTERS[params.get("status") ?? "all"];
  if (!keep) return adminError(422, "VALIDATION_ERROR", "status는 all·active·suspended 중 하나입니다.");
  const items = [...accounts.values()]
    .map((account) => account.user)
    .filter((user) => user.username.includes(q) && (!role || user.role === role) && keep(user))
    .sort((a, b) => a.username.localeCompare(b.username));
  return Response.json({ items });
}

export async function POST(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const body = await request.json().catch(() => null);
  const username = typeof body?.username === "string" ? body.username : "";
  if (!USERNAME.test(username)) {
    return adminError(400, "INVALID_USERNAME", "계정명은 영문 소문자·숫자로 시작하는 3~32자(소문자·숫자·. _ -)여야 합니다.");
  }
  const weak = weakPassword(body?.password);
  if (weak) return weak;
  if (accounts.has(username)) return adminError(409, "USERNAME_TAKEN", `이미 있는 계정명입니다: ${username}`);
  const role = body?.role === "operator" ? "operator" : "viewer";
  const user: AdminUser = {
    username, role, is_active: true, created_at: new Date().toISOString(), last_login_at: null, active_sessions: 0,
  };
  accounts.set(username, { user, sessions: [] });
  recordAudit(me, "user.create", username, `역할 ${role}`);
  return Response.json(user, { status: 201 });
}
