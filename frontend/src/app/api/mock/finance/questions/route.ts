import { planQuestionsOf } from "../../fixtures";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);

  // 실 API(FastAPI)와 같이 본문이 계약에 맞지 않으면 422.
  if (!body || typeof body.input !== "object" || body.input === null) {
    return Response.json(
      { error: { code: "INVALID_REQUEST", message: "input이 필요합니다" } },
      { status: 422 },
    );
  }

  return Response.json({ questions: planQuestionsOf(body) });
}
