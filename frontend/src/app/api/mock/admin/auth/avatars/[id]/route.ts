import { adminError, mockAdminFrom, unauthenticated } from "../../../../admin-fixtures";
import { accounts } from "../../../users/store";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const id = Number((await context.params).id);
  const avatar = [...accounts.values()][id - 1]?.avatar;
  if (!avatar) return adminError(404, "ADMIN_USER_NOT_FOUND", "프로필 사진이 없습니다.");
  return new Response(new Uint8Array(avatar.bytes), { headers: { "Content-Type": avatar.type } });
}
