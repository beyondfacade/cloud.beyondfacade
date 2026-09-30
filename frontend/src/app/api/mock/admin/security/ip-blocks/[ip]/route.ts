import { adminError, forbiddenRole, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { ipBlocks } from "../store";

export async function DELETE(request: Request, { params }: { params: Promise<{ ip: string }> }) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  if (!me.can_operate) return forbiddenRole();
  const ip = decodeURIComponent((await params).ip);
  if (!ipBlocks.delete(ip)) return adminError(404, "IP_BLOCK_NOT_FOUND", `차단 목록에 없는 IP입니다: ${ip}`);
  return new Response(null, { status: 204 });
}
