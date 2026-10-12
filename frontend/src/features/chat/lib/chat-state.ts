import type { ChatEvent, ChatMessage, ChatPage, ChatRoom } from "@/shared/api/types";

/** 서버 규칙(apps/chat/domain/services/chat_policy.py)과 같은 값 — 화면은 미리 막기만, 판정은 서버. */
export const MAX_BODY_LENGTH = 500;
export const BADGE_CAP = 99;

export const isMine = (message: Pick<ChatMessage, "sender_username">, me: string) => message.sender_username === me;

export function canSend(text: string): boolean {
  const length = text.trim().length;
  return length > 0 && length <= MAX_BODY_LENGTH;
}

/** 실시간으로 받은 메시지를 열어 둔 방 목록 끝에 — 내가 보낸 응답과 스트림이 같은 메시지를 두 번 줄 수 있어 id로 거른다. */
export function appendMessage(page: ChatPage | undefined, message: ChatMessage): ChatPage | undefined {
  if (!page || page.items.some((item) => item.id === message.id)) return page;
  return { ...page, items: [...page.items, message] };
}

export function prependOlder(page: ChatPage | undefined, older: ChatPage): ChatPage {
  const known = new Set(page?.items.map((item) => item.id));
  return { items: [...older.items.filter((item) => !known.has(item.id)), ...(page?.items ?? [])], has_more: older.has_more };
}

const redact = (message: ChatMessage, id: number): ChatMessage => {
  if (message.id === id) return { ...message, body: null, deleted: true };
  if (message.reply_to?.id === id) return { ...message, reply_to: { ...message.reply_to, preview: null, deleted: true } };
  return message;
};

/** 지운 메시지는 자리만 남기고, 그 메시지를 인용한 답장의 미리보기도 함께 가린다. */
export function markDeleted(page: ChatPage | undefined, id: number): ChatPage | undefined {
  return page && { ...page, items: page.items.map((item) => redact(item, id)) };
}

export interface RoomContext {
  me: string;
  /** 지금 화면에 띄워 둔 방 — 창을 닫았으면 null. 띄워 둔 방의 새 메시지는 바로 읽은 것으로 본다. */
  activeRoom: string | null;
}

/** 방 목록에 이벤트를 반영한다. 목록에 없는 방(처음 온 1:1)이면 null — 상대 이름을 모르니 서버에서 다시 받는다. */
export function applyEventToRooms(rooms: ChatRoom[], event: ChatEvent, context: RoomContext): ChatRoom[] | null {
  const index = rooms.findIndex((room) => room.key === event.room);
  if (index < 0) return event.type === "message" ? null : rooms;
  const room = rooms[index];
  const replaceAt = (next: ChatRoom) => rooms.map((r, i) => (i === index ? next : r));
  if (event.type === "deleted") {
    if (room.last_message?.id !== event.message_id) return rooms;
    return replaceAt({ ...room, last_message: redact(room.last_message, event.message_id) });
  }
  const counts = !isMine(event.message, context.me) && context.activeRoom !== event.room;
  const updated = { ...room, last_message: event.message, unread: room.unread + (counts ? 1 : 0) };
  if (room.kind !== "direct") return replaceAt(updated);
  // 1:1 대화는 최근 대화가 맨 위
  const others = rooms.filter((_, i) => i !== index);
  return [...others.filter((r) => r.kind !== "direct"), updated, ...others.filter((r) => r.kind === "direct")];
}

export function clearUnread(rooms: ChatRoom[], key: string): ChatRoom[] {
  return rooms.map((room) => (room.key === key && room.unread > 0 ? { ...room, unread: 0 } : room));
}

export const totalUnread = (rooms: ChatRoom[] | undefined) => (rooms ?? []).reduce((sum, room) => sum + room.unread, 0);

export function badgeLabel(count: number): string | null {
  if (count <= 0) return null;
  return count > BADGE_CAP ? `${BADGE_CAP}+` : String(count);
}

// 한국은 서머타임이 없어 +9시간 고정 — Intl 한국어 데이터가 없는 런타임에서도 같은 결과
const SEOUL_OFFSET_MS = 9 * 3_600_000;
const seoul = (date: Date) => new Date(date.getTime() + SEOUL_OFFSET_MS);
const dayKey = (date: Date) => seoul(date).toISOString().slice(0, 10);

/** 오늘 보낸 건 시각만("오후 3:04"), 그 전은 날짜까지("10월 11일 오후 3:04"). */
export function chatTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  const local = seoul(date);
  const hour = local.getUTCHours();
  const time = `${hour < 12 ? "오전" : "오후"} ${hour % 12 || 12}:${String(local.getUTCMinutes()).padStart(2, "0")}`;
  if (dayKey(date) === dayKey(now)) return time;
  return `${local.getUTCMonth() + 1}월 ${local.getUTCDate()}일 ${time}`;
}

/** 방 목록 한 줄 미리보기. */
export function lastLine(message: ChatMessage | null): string {
  if (!message) return "아직 메시지가 없어요";
  if (message.deleted) return "삭제된 메시지";
  return (message.body ?? "").split("\n")[0];
}
