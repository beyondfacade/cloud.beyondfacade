import { recordAudit } from "../../../security/audit/store";
import { operatorOnTarget } from "../../guard";
import { syncSessionCount } from "../../store";

export async function PATCH(request: Request, { params }: { params: Promise<{ username: string }> }) {
  const target = await operatorOnTarget(request, params);
  if ("error" in target) return target.error;
  const body = await request.json().catch(() => null);
  const active = body?.active === true;
  target.account.user = { ...target.account.user, is_active: active };
  if (!active) target.account.sessions = [];
  syncSessionCount(target.account);
  recordAudit(target.me, active ? "user.reactivate" : "user.suspend", target.username);
  return Response.json(target.account.user);
}
