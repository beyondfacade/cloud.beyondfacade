/** mock은 구글 버튼 화면을 확인할 수 있게 항상 켠다 — 실 API는 클라이언트 설정 유무를 답한다. */
export async function GET() {
  return Response.json({ google: true });
}
