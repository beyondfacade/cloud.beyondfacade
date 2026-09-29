export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const origin = process.env.BACKEND_ORIGIN;
  if (!origin) {
    return Response.json(
      { error: { code: "BACKEND_PROXY_DISABLED", message: "백엔드 프록시가 설정되지 않았습니다." } },
      { status: 404 },
    );
  }

  const { id } = await params;
  const upstream = await fetch(`${origin}/analysis/${id}/events`, {
    headers: { accept: "text/event-stream" },
    cache: "no-store",
    signal: request.signal,
  });
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
