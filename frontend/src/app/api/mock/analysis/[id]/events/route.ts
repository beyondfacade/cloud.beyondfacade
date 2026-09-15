import { agentEventScript } from "../../../fixtures";

export async function GET() {
  const script = agentEventScript();
  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder();
      for (const ev of script) {
        controller.enqueue(enc.encode(`event: ${ev.type}\ndata: ${JSON.stringify(ev)}\n\n`));
        await new Promise((r) => setTimeout(r, 400)); // 진행 패널 시연용 지연
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  });
}
