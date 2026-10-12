import { ApiError, apiDelete, apiGet, apiPost, apiPut } from "@/shared/api/client";
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

/** PDF 바이트를 본문 그대로 보낸다 — 1:1 대화에서만, 5MB 이하. */
export const sendChatAttachment = async (room: string, file: File) => {
  const res = await fetch(`${config.apiBase}${roomPath(room)}/attachments?name=${encodeURIComponent(file.name)}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/pdf" },
    body: file,
  });
  if (!res.ok) await apiError(res);
  return (await res.json()) as ChatMessage;
};

export const fetchChatAttachment = async (messageId: number) => {
  const res = await fetch(`${config.apiBase}/chat/messages/${messageId}/attachment`, { credentials: "include" });
  if (!res.ok) await apiError(res);
  return res.blob();
};

async function apiError(res: Response): Promise<never> {
  const body = await res.json().catch(() => null);
  throw new ApiError(body?.error?.code ?? `HTTP_${res.status}`, body?.error?.message ?? "파일을 처리하지 못했어요.");
}

export const deleteChatMessage = (id: number) => apiDelete(`/chat/messages/${id}`);

export const openDirectRoom = (userId: number) => apiPost<ChatRoom>("/chat/direct", { user_id: userId });

/** 일반 회원에게 보이는 전문가 목록(요금·상담 상태) — 다른 등급은 빈 목록. */
export const fetchChatExperts = () => apiGet<ChatExpert[]>("/chat/members");

/** 더미 구매(결제 없음) — 산 뒤 그 전문가와의 1:1 방을 돌려준다. */
export const buyConsultation = (expertId: number, hours: number) =>
  apiPost<ChatRoom>("/chat/consultations", { expert_id: expertId, hours });

export const markChatRead = (room: string, lastReadId: number) =>
  apiPut<ChatRead>(`/chat/reads/${encodeURIComponent(room)}`, { last_read_id: lastReadId });

export const chatStreamUrl = () => `${config.apiBase}/chat/stream`;
