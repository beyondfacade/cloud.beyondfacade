import type { AdminUser } from "@/shared/api/types";
import { adminError, mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { accounts } from "./store";

const STATUS_FILTERS: Record<string, (user: AdminUser) => boolean> = {
  all: () => true,
  active: (user) => user.is_active,
  suspended: (user) => !user.is_active,
};

/** 실 API처럼 목록만 — 계정은 공개 가입·CLI로만 생긴다(POST 없음 = 405). */
export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const params = new URL(request.url).searchParams;
  const q = (params.get("q") ?? "").trim().toLowerCase();
  const role = params.get("role");
  const keep = STATUS_FILTERS[params.get("status") ?? "all"];
  if (!keep) return adminError(422, "VALIDATION_ERROR", "status는 all·active·suspended 중 하나입니다.");
  const items = [...accounts.values()]
    .map((account) => account.user)
    .filter((user) => (user.username.includes(q) || (user.email ?? "").includes(q)) && (!role || user.role === role) && keep(user))
    .sort((a, b) => a.username.localeCompare(b.username));
  return Response.json({ items });
}
