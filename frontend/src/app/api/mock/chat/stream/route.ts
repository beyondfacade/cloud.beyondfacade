import { mockAdminFrom, unauthenticated } from "../../admin-fixtures";
import { messages } from "../store";

export const dynamic = "force-dynamic";

const LIFETIME_MS = 50_000;
const PING_MS = 15_000;

/** mock은 다른 사람이 없어 실시간으로 올 메시지가 없다 — ready 뒤 핑만 보내다 50초에 끊는다(실 API와 같은 수명). */
export async function GET(request: Request) {
  if (!mockAdminFrom(request)) return unauthenticated();
  const encoder = new TextEncoder();
  const latest = messages.at(-1)?.id ?? 0;
  let timers: ReturnType<typeof setTimeout>[] = [];
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(`retry: 3000\nid: ${latest}\nevent: ready\ndata: {}\n\n`));
      const stop = () => {
        timers.forEach(clearTimeout);
        timers = [];
        try {
          controller.close();
        } catch {
          // 이미 닫힘
        }
      };
      const ping = setInterval(() => controller.enqueue(encoder.encode(": ping\n\n")), PING_MS);
      timers = [ping, setTimeout(stop, LIFETIME_MS)];
      request.signal.addEventListener("abort", stop);
    },
    cancel() {
      timers.forEach(clearTimeout);
    },
  });
  return new Response(stream, { headers: { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-cache" } });
}
