import { intentOfCodes, intentOfText } from "../fixtures";

/** 실 API 미러 — 두 형태(text / region_code+industry_id). 빈 문장은 400, 파싱 실패는 실패가 아니다(C유형 200). */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as {
    text?: string; region_code?: string; industry_id?: string;
  };

  if (body.region_code && body.industry_id) {
    return Response.json(intentOfCodes(body.region_code, body.industry_id));
  }

  const text = (body.text ?? "").trim();
  if (!text) {
    return Response.json(
      { error: { code: "INTENT_TEXT_EMPTY", message: "문장이 비어 있습니다." } },
      { status: 400 },
    );
  }
  return Response.json(intentOfText(text));
}
