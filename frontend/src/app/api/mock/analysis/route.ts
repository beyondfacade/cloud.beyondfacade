import { isKnownIndustry } from "@/shared/industries";
import { SEOUL_REGIONS_GEOJSON } from "../fixtures";

/** 필수 값·예산 오류는 400, 실 API처럼 미등록 동·업종은 404로 응답한다. */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as {
    region?: unknown; industry?: unknown; budget?: unknown; question?: unknown;
  } | null;
  if (
    typeof body?.region !== "string" || !body.region.trim() ||
    typeof body.industry !== "string" || !body.industry.trim() ||
    (body.budget !== undefined && (typeof body.budget !== "number" || !Number.isInteger(body.budget) || body.budget < 0))
  ) {
    return Response.json(
      { error: { code: "INVALID_ANALYSIS_REQUEST", message: "지역과 업종은 필수이며 예산은 0 이상의 정수여야 합니다." } },
      { status: 400 },
    );
  }
  if (!SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === body.region)) {
    return Response.json(
      { error: { code: "REGION_NOT_FOUND", message: `알 수 없는 region_code: ${body.region}` } },
      { status: 404 },
    );
  }
  if (!isKnownIndustry(body.industry)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `지원하지 않는 industry: ${body.industry}` } },
      { status: 404 },
    );
  }
  // mock은 요청 저장소 없이 ID에 질문 유무만 실어 SSE까지 전달한다.
  const prefix = typeof body.question === "string" && body.question.trim() ? "question-" : "";
  return Response.json({ analysis_id: `${prefix}${crypto.randomUUID()}` });
}
