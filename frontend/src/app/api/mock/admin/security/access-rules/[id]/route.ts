import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { recordAudit } from "../../audit/store";
import { accessRules } from "../store";

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const id = Number((await params).id);
  const index = accessRules.findIndex((rule) => rule.id === id);
  if (index < 0) return adminError(404, "ACCESS_RULE_NOT_FOUND", `목록에 없는 항목입니다: ${id}`);
  const [removed] = accessRules.splice(index, 1);
  recordAudit(me, "access_rule.delete", removed.value, removed.policy === "allow" ? "화이트리스트" : "블랙리스트");
  return new Response(null, { status: 204 });
}
