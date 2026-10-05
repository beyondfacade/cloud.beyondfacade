/** 실 API의 요청 검증을 미러하되 mock은 §15 에러 바디와 400으로 응답한다. */
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
  // mock은 요청 저장소 없이 ID에 질문 유무만 실어 SSE까지 전달한다.
  const prefix = typeof body.question === "string" && body.question.trim() ? "question-" : "";
  return Response.json({ analysis_id: `${prefix}${crypto.randomUUID()}` });
}
