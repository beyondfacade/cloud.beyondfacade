import { describe, expect, it } from "vitest";
import type { ChatEvent, ChatMessage, ChatPage, ChatRoom } from "@/shared/api/types";
import {
  appendMessage,
  applyEventToRooms,
  badgeLabel,
  canSend,
  chatTime,
  clearUnread,
  lastLine,
  markDeleted,
  prependOlder,
  totalUnread,
} from "./chat-state";

const message = (id: number, over: Partial<ChatMessage> = {}): ChatMessage => ({
  id, room: "global", sender_id: 2, sender_username: "viewer", sender_role: "viewer", body: `메시지 ${id}`,
  deleted: false, created_at: "2026-10-12T03:00:00Z", reply_to: null, ...over,
});
const room = (key: string, over: Partial<ChatRoom> = {}): ChatRoom => ({
  key, kind: key.startsWith("dm:") ? "direct" : (key as ChatRoom["kind"]), title: key, partner_id: null, unread: 0,
  last_message: null, ...over,
});
const sent = (m: ChatMessage): ChatEvent => ({ type: "message", room: m.room, message_id: m.id, message: m });
const page = (...items: ChatMessage[]): ChatPage => ({ items, has_more: false });

describe("메시지 목록", () => {
  it("새 메시지는 끝에 붙고, 같은 id가 다시 오면 무시한다", () => {
    const once = appendMessage(page(message(1)), message(2));
    expect(once?.items.map((m) => m.id)).toEqual([1, 2]);
    expect(appendMessage(once, message(2))).toBe(once);
  });

  it("아직 불러오지 않은 방이면 아무것도 만들지 않는다", () => {
    expect(appendMessage(undefined, message(1))).toBeUndefined();
  });

  it("이전 메시지는 앞에 붙이고 더 있는지 여부를 갱신한다", () => {
    const merged = prependOlder({ items: [message(3)], has_more: true }, { items: [message(1), message(2)], has_more: false });
    expect([merged.items.map((m) => m.id), merged.has_more]).toEqual([[1, 2, 3], false]);
  });

  it("지우면 본문을 가리고, 그 메시지를 인용한 답장 미리보기도 가린다", () => {
    const reply = message(2, { reply_to: { id: 1, sender_username: "viewer", preview: "메시지 1", deleted: false } });
    const [gone, quoted] = markDeleted(page(message(1), reply), 1)!.items;
    expect([gone.body, gone.deleted]).toEqual([null, true]);
    expect(quoted.reply_to).toEqual({ id: 1, sender_username: "viewer", preview: null, deleted: true });
    expect(quoted.body).toBe("메시지 2");
  });
});

describe("방 목록", () => {
  const rooms = [room("global"), room("operators"), room("dm:1:2", { title: "viewer" }), room("dm:1:3", { title: "guest" })];

  it("남이 보낸 메시지는 안 읽음을 늘리고, 내 메시지나 띄워 둔 방은 늘리지 않는다", () => {
    const viewerSays = sent(message(5));
    expect(applyEventToRooms(rooms, viewerSays, { me: "ops", activeRoom: null })![0].unread).toBe(1);
    expect(applyEventToRooms(rooms, viewerSays, { me: "viewer", activeRoom: null })![0].unread).toBe(0);
    expect(applyEventToRooms(rooms, viewerSays, { me: "ops", activeRoom: "global" })![0].unread).toBe(0);
    expect(applyEventToRooms(rooms, viewerSays, { me: "ops", activeRoom: null })![0].last_message?.id).toBe(5);
  });

  it("1:1 대화에 새 메시지가 오면 1:1 중 맨 위로 올린다", () => {
    const next = applyEventToRooms(rooms, sent(message(6, { room: "dm:1:3", sender_username: "guest" })), { me: "ops", activeRoom: null });
    expect(next!.map((r) => r.key)).toEqual(["global", "operators", "dm:1:3", "dm:1:2"]);
  });

  it("목록에 없는 방의 메시지면 null — 서버에서 목록을 다시 받아야 한다", () => {
    expect(applyEventToRooms(rooms, sent(message(7, { room: "dm:1:9" })), { me: "ops", activeRoom: null })).toBeNull();
  });

  it("마지막 메시지가 지워지면 미리보기를 가리고, 다른 메시지 삭제는 그대로 둔다", () => {
    const withLast = [room("global", { last_message: message(8) })];
    const deleted = (id: number): ChatEvent => ({ type: "deleted", room: "global", message_id: id, message: null });
    expect(applyEventToRooms(withLast, deleted(8), { me: "ops", activeRoom: null })![0].last_message?.deleted).toBe(true);
    expect(applyEventToRooms(withLast, deleted(3), { me: "ops", activeRoom: null })).toBe(withLast);
  });

  it("읽으면 그 방만 0이 되고, 합계와 배지는 99를 넘으면 99+", () => {
    const counted = [room("global", { unread: 3 }), room("dm:1:2", { unread: 2 })];
    expect(totalUnread(clearUnread(counted, "global"))).toBe(2);
    expect(totalUnread(undefined)).toBe(0);
    expect([badgeLabel(0), badgeLabel(7), badgeLabel(99), badgeLabel(100)]).toEqual([null, "7", "99", "99+"]);
  });
});

describe("보내기·표시", () => {
  it("공백만이거나 500자를 넘으면 보낼 수 없다", () => {
    expect([canSend("  "), canSend(" 안녕 "), canSend("가".repeat(500)), canSend("가".repeat(501))]).toEqual([false, true, true, false]);
  });

  it("오늘 메시지는 시각만, 지난 메시지는 날짜까지 서울 시각으로 보여 준다", () => {
    const now = new Date("2026-10-12T06:00:00Z"); // 서울 오후 3시
    expect(chatTime("2026-10-12T06:04:00Z", now)).toBe("오후 3:04");
    expect(chatTime("2026-10-11T00:30:00Z", now)).toBe("10월 11일 오전 9:30");
  });

  it("방 목록 미리보기는 첫 줄, 지워졌거나 없으면 안내 문구", () => {
    expect(lastLine(message(1, { body: "첫 줄\n둘째 줄" }))).toBe("첫 줄");
    expect(lastLine(message(1, { body: null, deleted: true }))).toBe("삭제된 메시지");
    expect(lastLine(null)).toBe("아직 메시지가 없어요");
  });
});
