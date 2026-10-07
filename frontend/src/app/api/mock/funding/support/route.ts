import type { SupportGuide } from "@/shared/api/types";
import { supportGuideOf } from "../../fixtures";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim().slice(0, 200) ?? "";
  // 실 API와 같은 계약 — 둘 다 선택이고, 동이 없으면 구 묶음이 빈다.
  const guide: SupportGuide = supportGuideOf(searchParams.get("region"), searchParams.get("industry"), q);
  return Response.json(guide);
}
