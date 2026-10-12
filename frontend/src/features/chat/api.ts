import { apiDelete, apiGet, apiPost, apiPut } from "@/shared/api/client";
import type { ChatMessage, ChatPage, ChatPeer, ChatRead, ChatRoom } from "@/shared/api/types";
import { config } from "@/shared/config";

/** 로그인·로그아웃 때 이 접두어 아래 캐시를 통째로 버린다 (replaceSession). */
export const CHAT_QUERY_KEY = ["chat"] as const;
export const chatRoomsKey = [...CHAT_QUERY_KEY, "rooms"] as const;
export const chatMessagesKey = (room: string) => [...CHAT_QUERY_KEY, "messages", room] as const;

const roomPath = (room: string) => `/chat/rooms/${encodeURIComponent(room)}`;

export const fetchChatRooms = () => apiGet<ChatRoom[]>("/chat/rooms");

export const fetchChatMessages = (room: string, beforeId?: number) =>
  apiGet<ChatPage>(`${roomPath(room)}/messages${beforeId ? `?before_id=${beforeId}` : ""}`);

export const sendChatMessage = (room: string, body: string, replyToId: number | null) =>
  apiPost<ChatMessage>(`${roomPath(room)}/messages`, { body, reply_to_id: replyToId });

export const deleteChatMessage = (id: number) => apiDelete(`/chat/messages/${id}`);

export const openDirectRoom = (userId: number) => apiPost<ChatRoom>("/chat/direct", { user_id: userId });

export const openExpertRoom = () => apiPost<ChatRoom>("/chat/expert", {});

export const searchChatMembers = (q: string) => apiGet<ChatPeer[]>(`/chat/members?q=${encodeURIComponent(q)}`);

export const markChatRead = (room: string, lastReadId: number) =>
  apiPut<ChatRead>(`/chat/reads/${encodeURIComponent(room)}`, { last_read_id: lastReadId });

export const chatStreamUrl = () => `${config.apiBase}/chat/stream`;
