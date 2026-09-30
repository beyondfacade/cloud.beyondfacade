import { recordAudit } from "../../../security/audit/store";
import { operatorOnTarget } from "../../guard";

export async function PATCH(request: Request, { params }: { params: Promise<{ username: string }> }) {
  const target = await operatorOnTarget(request, params);
  if ("error" in target) return target.error;
  const body = await request.json().catch(() => null);
  const role = body?.role === "operator" ? "operator" : "viewer";
  const before = target.account.user.role;
  target.account.user = { ...target.account.user, role };
  recordAudit(target.me, "user.role", target.username, `${before} → ${role}`);
  return Response.json(target.account.user);
}
