import type { QueryClient } from "@tanstack/react-query";
import type { ChatEvent, ChatPage, ChatRoom } from "@/shared/api/types";
import { chatMessagesKey, chatRoomsKey } from "../api";
import { appendMessage, applyEventToRooms, clearUnread, markDeleted, type RoomContext } from "../lib/chat-state";

/** 실시간 이벤트·내가 보낸 응답을 캐시에 반영한다 — 같은 메시지가 두 경로로 와도 한 번만 들어간다. */
export function applyChatEvent(client: QueryClient, event: ChatEvent, context: RoomContext): void {
  client.setQueryData<ChatPage>(chatMessagesKey(event.room), (page) =>
    event.type === "message" ? appendMessage(page, event.message) : markDeleted(page, event.message_id),
  );
  const rooms = client.getQueryData<ChatRoom[]>(chatRoomsKey);
  if (!rooms) return;
  const next = applyEventToRooms(rooms, event, context);
  if (next) client.setQueryData(chatRoomsKey, next);
  else void client.invalidateQueries({ queryKey: chatRoomsKey });
}

export function clearRoomUnread(client: QueryClient, room: string): void {
  client.setQueryData<ChatRoom[]>(chatRoomsKey, (rooms) => rooms && clearUnread(rooms, room));
}
