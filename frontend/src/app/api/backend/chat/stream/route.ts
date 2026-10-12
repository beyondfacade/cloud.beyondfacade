export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** 개발 서버 전용 채팅 SSE 프록시 — rewrite는 응답을 모아 보내 실시간이 끊긴다.
 *  로그인 쿠키와 재접속 위치(Last-Event-ID)를 백엔드로 넘겨야 한다. */
export async function GET(request: Request) {
  const origin = process.env.BACKEND_ORIGIN;
  if (!origin) {
    return Response.json(
      { error: { code: "BACKEND_PROXY_DISABLED", message: "백엔드 프록시가 설정되지 않았습니다." } },
      { status: 404 },
    );
  }

  const headers: Record<string, string> = { accept: "text/event-stream" };
  for (const name of ["cookie", "last-event-id"]) {
    const value = request.headers.get(name);
    if (value) headers[name] = value;
  }
  const upstream = await fetch(`${origin}/chat/stream`, { headers, cache: "no-store", signal: request.signal });
  if (!upstream.ok) {
    return new Response(upstream.body, { status: upstream.status, headers: { "content-type": "application/json" } });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      "x-accel-buffering": "no",
    },
  });
}
