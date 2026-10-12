import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatMessage, ChatRoom } from "@/shared/api/types";
import { POST as buyConsultation } from "./consultations/route";
import { POST as openDirect } from "./direct/route";
import { GET as members } from "./members/route";
import { GET as downloadPdf } from "./messages/[id]/attachment/route";
import { DELETE as remove } from "./messages/[id]/route";
import { POST as uploadPdf } from "./rooms/[room]/attachments/route";
import { PUT as markRead } from "./reads/[room]/route";
import { GET as listMessages, POST as postMessage } from "./rooms/[room]/messages/route";
import { GET as listRooms } from "./rooms/route";
import { consultations } from "./store";
import { GET as stream } from "./stream/route";

const as = (username: string | null): Record<string, string> => (username ? { cookie: `metabole_admin=${username}` } : {});
const base = "http://test/api/mock/chat";
const roomCtx = (room: string) => ({ params: Promise.resolve({ room: encodeURIComponent(room) }) });
const json = (method: string, body: unknown, user: string) => ({
  method, headers: { ...as(user), "content-type": "application/json" }, body: JSON.stringify(body),
});

const rooms = async (user: string): Promise<ChatRoom[]> => (await listRooms(new Request(`${base}/rooms`, { headers: as(user) }))).json();
const page = (room: string, user: string, query = "") =>
  listMessages(new Request(`${base}/rooms/${encodeURIComponent(room)}/messages${query}`, { headers: as(user) }), roomCtx(room));
const post = (room: string, user: string, body: string, replyToId: number | null = null) =>
  postMessage(new Request(`${base}/rooms/${room}/messages`, json("POST", { body, reply_to_id: replyToId }, user)), roomCtx(room));
const errorCode = async (response: Response) => (await response.json()).error.code;

let clock = Date.parse("2026-10-12T03:00:00Z");
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  clock += 60_000; // 테스트마다 도배 제한 창(10초)을 벗어난다
  vi.setSystemTime(clock);
});
afterAll(() => vi.useRealTimers());

describe("채팅 mock 계약", () => {
  it("비로그인은 모든 채팅 API가 401 UNAUTHENTICATED", async () => {
    expect((await listRooms(new Request(`${base}/rooms`))).status).toBe(401);
    expect(await errorCode(await page("global", ""))).toBe("UNAUTHENTICATED");
    expect((await stream(new Request(`${base}/stream`))).status).toBe(401);
  });

  it("일반 회원은 전체방만, 관리자는 관리자방까지 — 응답 필드는 실 API와 같다", async () => {
    expect((await rooms("viewer")).map((r) => r.key)).toEqual(["global"]);
    const opsRooms = await rooms("ops");
    expect(opsRooms.map((r) => [r.key, r.title])).toEqual([["global", "전체"], ["operators", "관리자"]]);
    expect(Object.keys(opsRooms[0]).sort()).toEqual(["key", "kind", "last_message", "partner_avatar_version", "partner_id", "title", "unread"]);
    const { items, has_more } = await (await page("global", "viewer")).json();
    expect(has_more).toBe(false);
    expect(Object.keys(items[0]).sort()).toEqual(
      ["attachment", "body", "created_at", "deleted", "id", "reply_to", "room", "sender_id", "sender_role", "sender_username"],
    );
  });

  it("관리자방은 일반 회원에게 403, 모르는 방은 404", async () => {
    expect(await errorCode(await page("operators", "viewer"))).toBe("CHAT_ROOM_FORBIDDEN");
    expect((await post("operators", "viewer", "몰래")).status).toBe(403);
    expect((await page("lobby", "viewer")).status).toBe(404);
  });

  it("보내면 201로 다듬은 본문이 오고, 빈 메시지·500자 초과는 400", async () => {
    const sent = await post("global", "viewer", "  안녕하세요  ");
    expect(sent.status).toBe(201);
    expect(((await sent.json()) as ChatMessage).body).toBe("안녕하세요");
    expect(await errorCode(await post("global", "viewer", "   "))).toBe("INVALID_CHAT_MESSAGE");
    expect((await post("global", "viewer", "가".repeat(501))).status).toBe(400);
  });

  it("10초에 5개를 넘기면 429 CHAT_TOO_FAST", async () => {
    for (let i = 0; i < 5; i += 1) expect((await post("global", "ops", `도배 ${i}`)).status).toBe(201);
    expect(await errorCode(await post("global", "ops", "여섯 번째"))).toBe("CHAT_TOO_FAST");
  });

  it("답장은 원문 첫 줄 미리보기, 다른 방 메시지에는 404", async () => {
    const original: ChatMessage = await (await post("global", "ops", "첫 줄\n둘째 줄")).json();
    const reply: ChatMessage = await (await post("global", "viewer", "답장", original.id)).json();
    expect(reply.reply_to).toEqual({ id: original.id, sender_username: "ops", preview: "첫 줄", deleted: false });
    const secret: ChatMessage = await (await post("operators", "ops", "관리자방 글")).json();
    expect(await errorCode(await post("global", "ops", "엉뚱한 답장", secret.id))).toBe("CHAT_MESSAGE_NOT_FOUND");
  });

  it("삭제는 관리자만 — 본문이 사라지고 답장 미리보기도 가려진다", async () => {
    const original: ChatMessage = await (await post("global", "viewer", "지울 글")).json();
    await post("global", "viewer", "그 글에 답장", original.id);
    const del = (user: string, id: number) =>
      remove(new Request(`${base}/messages/${id}`, { method: "DELETE", headers: as(user) }), { params: Promise.resolve({ id: String(id) }) });
    expect(await errorCode(await del("viewer", original.id))).toBe("FORBIDDEN_ROLE");
    expect((await del("ops", original.id)).status).toBe(204);
    expect((await del("ops", 99_999)).status).toBe(404);
    const items: ChatMessage[] = (await (await page("global", "ops")).json()).items;
    const gone = items.find((m) => m.id === original.id)!;
    expect([gone.body, gone.deleted]).toEqual([null, true]);
    expect(items.at(-1)!.reply_to).toMatchObject({ preview: null, deleted: true });
  });

  it("일반 회원은 전문가만 찾아 1:1을 열고, 메시지가 오가면 전문가의 방 목록에 안 읽음과 함께 생긴다", async () => {
    const expert = { id: 5, username: "park.expert", specialty: "카페", hourly_rate: 30_000, status: "available", avatar_version: null };
    const found = await (await members(new Request(`${base}/members?q=E`, { headers: as("viewer") }))).json();
    expect(found).toEqual([expert]);
    expect(await (await members(new Request(`${base}/members`, { headers: as("viewer") }))).json()).toEqual([expert]);
    const room: ChatRoom = await (await openDirect(new Request(`${base}/direct`, json("POST", { user_id: 5 }, "viewer")))).json();
    expect([room.key, room.kind, room.title, room.partner_id]).toEqual(["dm:2:5", "direct", "park.expert", 5]);
    expect(await errorCode(await openDirect(new Request(`${base}/direct`, json("POST", { user_id: 2 }, "viewer"))))).toBe("CHAT_MEMBER_NOT_FOUND");
    expect((await post("dm:2:5", "viewer", "안녕하세요")).status).toBe(201);
    const dm = (await rooms("park.expert")).find((r) => r.key === "dm:2:5")!;
    expect([dm.title, dm.unread]).toEqual(["viewer", 1]);
    expect((await post("dm:2:5", "park.expert", "네 말씀하세요")).status).toBe(201);
    expect((await page("dm:2:5", "ops")).status).toBe(403);
  });

  it("1:1은 일반 회원이 전문가에게만 걸고, 다른 조합은 403에 찾기 결과도 없다", async () => {
    expect(await errorCode(await openDirect(new Request(`${base}/direct`, json("POST", { user_id: 1 }, "viewer"))))).toBe("CHAT_ROOM_FORBIDDEN");
    expect((await openDirect(new Request(`${base}/direct`, json("POST", { user_id: 2 }, "park.expert")))).status).toBe(403);
    expect(await (await members(new Request(`${base}/members?q=v`, { headers: as("park.expert") }))).json()).toEqual([]);
    expect((await post("dm:1:2", "viewer", "관리자님?")).status).toBe(403);
  });

  it("상담을 사면 201로 1:1 방이 오고, 다른 회원이 산 상담 중인 전문가에게는 409 — 끝나면 다시 대화 가능", async () => {
    const buy = (user: string, hours: number) =>
      buyConsultation(new Request(`${base}/consultations`, json("POST", { expert_id: 5, hours }, user)));
    const status = async () => (await (await members(new Request(`${base}/members`, { headers: as("viewer") }))).json())[0].status;
    expect(await errorCode(await buy("viewer", 4))).toBe("INVALID_CONSULTATION");
    expect((await buy("park.expert", 1)).status).toBe(403);
    const bought = await buy("viewer", 1);
    expect([bought.status, ((await bought.json()) as ChatRoom).key]).toEqual([201, "dm:2:5"]);
    expect(await status()).toBe("mine");
    consultations.splice(0, consultations.length, { viewerId: 4, expertId: 5, endsAt: Date.now() + 60_000 });
    expect(await status()).toBe("busy");
    expect(await errorCode(await openDirect(new Request(`${base}/direct`, json("POST", { user_id: 5 }, "viewer"))))).toBe("CHAT_EXPERT_BUSY");
    expect((await buy("viewer", 1)).status).toBe(409);
    vi.setSystemTime(Date.now() + 60_000);
    expect(await status()).toBe("available");
    consultations.length = 0;
  });

  it("1:1 대화에만 PDF를 올리고, 그 방 회원만 내려받는다", async () => {
    const upload = (room: string, user: string, name: string, body: string) =>
      uploadPdf(
        new Request(`${base}/rooms/${room}/attachments?name=${encodeURIComponent(name)}`, {
          method: "POST", headers: { ...as(user), "content-type": "application/pdf" }, body,
        }),
        roomCtx(room),
      );
    const download = (id: number, user: string) =>
      downloadPdf(new Request(`${base}/messages/${id}/attachment`, { headers: as(user) }), { params: Promise.resolve({ id: String(id) }) });
    const sent = await upload("dm:2:5", "viewer", "자료.pdf", "%PDF-1.4 본문");
    const message: ChatMessage = await sent.json();
    expect([sent.status, message.body, message.attachment?.name]).toEqual([201, "자료.pdf", "자료.pdf"]);
    const file = await download(message.id, "park.expert");
    expect([file.status, file.headers.get("content-type"), await file.text()]).toEqual([200, "application/pdf", "%PDF-1.4 본문"]);
    expect((await download(message.id, "ops")).status).toBe(404);
    expect(await errorCode(await upload("dm:2:5", "viewer", "메모.txt", "%PDF-1.4"))).toBe("INVALID_CHAT_ATTACHMENT");
    expect(await errorCode(await upload("global", "viewer", "a.pdf", "%PDF-1.4"))).toBe("CHAT_ROOM_FORBIDDEN");
  });

  it("읽음 표시는 앞으로만 가고, 읽으면 안 읽은 개수가 0이 된다", async () => {
    const read = (room: string, user: string, id: number) =>
      markRead(new Request(`${base}/reads/${room}`, json("PUT", { last_read_id: id }, user)), roomCtx(room));
    const latest = (await rooms("ops")).find((r) => r.key === "global")!.last_message!.id;
    expect((await (await read("global", "ops", latest)).json()).last_read_id).toBe(latest);
    expect((await rooms("ops")).find((r) => r.key === "global")!.unread).toBe(0);
    expect((await (await read("global", "ops", 1)).json()).last_read_id).toBe(latest);
    expect((await read("operators", "viewer", 1)).status).toBe(403);
  });

  it("스트림은 SSE로 ready 이벤트부터 보낸다", async () => {
    const controller = new AbortController();
    const response = await stream(new Request(`${base}/stream`, { headers: as("viewer"), signal: controller.signal }));
    expect(response.headers.get("content-type")).toBe("text/event-stream; charset=utf-8");
    const reader = response.body!.getReader();
    const first = new TextDecoder().decode((await reader.read()).value);
    expect(first).toMatch(/^retry: 3000\nid: \d+\nevent: ready\n/);
    controller.abort();
    expect((await reader.read()).done).toBe(true);
  });
});
