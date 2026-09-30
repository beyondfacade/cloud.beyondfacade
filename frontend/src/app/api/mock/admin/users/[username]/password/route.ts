import { recordAudit } from "../../../security/audit/store";
import { operatorOnTarget, weakPassword } from "../../guard";
import { syncSessionCount } from "../../store";

export async function PUT(request: Request, { params }: { params: Promise<{ username: string }> }) {
  const target = await operatorOnTarget(request, params);
  if ("error" in target) return target.error;
  const body = await request.json().catch(() => null);
  const weak = weakPassword(body?.password);
  if (weak) return weak;
  target.account.sessions = [];
  syncSessionCount(target.account);
  recordAudit(target.me, "user.password_reset", target.username);
  return new Response(null, { status: 204 });
}
