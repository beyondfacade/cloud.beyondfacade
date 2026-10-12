import { apiDelete, apiGet, apiPost, apiPut } from "@/shared/api/client";
import type { ChatExpert, ChatMessage, ChatPage, ChatRead, ChatRoom } from "@/shared/api/types";
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

/** 일반 회원에게 보이는 전문가 목록(요금·상담 상태) — 다른 등급은 빈 목록. */
export const fetchChatExperts = () => apiGet<ChatExpert[]>("/chat/members");

/** 더미 구매(결제 없음) — 산 뒤 그 전문가와의 1:1 방을 돌려준다. */
export const buyConsultation = (expertId: number, hours: number) =>
  apiPost<ChatRoom>("/chat/consultations", { expert_id: expertId, hours });

export const markChatRead = (room: string, lastReadId: number) =>
  apiPut<ChatRead>(`/chat/reads/${encodeURIComponent(room)}`, { last_read_id: lastReadId });

export const chatStreamUrl = () => `${config.apiBase}/chat/stream`;
