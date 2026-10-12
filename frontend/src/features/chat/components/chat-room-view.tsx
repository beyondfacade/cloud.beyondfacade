"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/api/client";
import type { AdminMe, ChatMessage, ChatPage } from "@/shared/api/types";
import { chatMessagesKey, deleteChatMessage, fetchChatMessages, markChatRead, sendChatMessage } from "../api";
import { applyChatEvent, clearRoomUnread } from "../hooks/chat-cache";
import { isMine, prependOlder } from "../lib/chat-state";
import { ChatComposer } from "./chat-composer";
import { ChatMessageItem } from "./chat-message-item";
import styles from "./global-chat.module.css";

const NEAR_BOTTOM_PX = 80;

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : "잠시 후 다시 시도해 주세요.");

export function ChatRoomView({ room, me, emptyText }: { room: string; me: AdminMe; emptyText: string }) {
  const client = useQueryClient();
  const key = chatMessagesKey(room);
  const { data, isPending, isError } = useQuery({ queryKey: key, queryFn: () => fetchChatMessages(room) });
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const listRef = useRef<HTMLUListElement>(null);
  const stickToBottom = useRef(true);
  const markedUpTo = useRef(0);
  const lastId = data?.items.at(-1)?.id ?? 0;

  const send = useMutation({
    mutationFn: (body: string) => sendChatMessage(room, body, replyTo?.id ?? null),
    onSuccess: (message) => {
      stickToBottom.current = true;
      setReplyTo(null);
      applyChatEvent(client, { type: "message", room, message_id: message.id, message }, { me: me.username, activeRoom: room });
    },
  });
  const remove = useMutation({
    mutationFn: (message: ChatMessage) => deleteChatMessage(message.id),
    onSuccess: (_, message) =>
      applyChatEvent(client, { type: "deleted", room, message_id: message.id, message: null }, { me: me.username, activeRoom: room }),
  });

  // 띄워 둔 방의 마지막 메시지까지 읽은 것으로 — 같은 위치를 두 번 보내지 않는다
  useEffect(() => {
    if (lastId <= markedUpTo.current) return;
    markedUpTo.current = lastId;
    clearRoomUnread(client, room);
    markChatRead(room, lastId).catch(() => {
      markedUpTo.current = 0;
    });
  }, [client, room, lastId]);

  useLayoutEffect(() => {
    const list = listRef.current;
    if (list && stickToBottom.current) list.scrollTop = list.scrollHeight;
  }, [lastId]);

  const onScroll = () => {
    const list = listRef.current;
    if (list) stickToBottom.current = list.scrollHeight - list.scrollTop - list.clientHeight < NEAR_BOTTOM_PX;
  };

  const loadOlder = async () => {
    const first = data?.items[0];
    if (!first) return;
    setLoadingOlder(true);
    try {
      const older = await fetchChatMessages(room, first.id);
      client.setQueryData<ChatPage>(key, (page) => prependOlder(page, older));
    } finally {
      setLoadingOlder(false);
    }
  };

  const onDelete = (message: ChatMessage) => {
    if (window.confirm("이 메시지를 삭제할까요? 모든 사람에게서 사라집니다.")) remove.mutate(message);
  };

  return (
    <>
      <ul ref={listRef} className={styles.list} onScroll={onScroll} aria-live="polite" aria-label="메시지 목록">
        {data?.has_more && (
          <li>
            <button type="button" className={styles.more} onClick={loadOlder} disabled={loadingOlder}>
              {loadingOlder ? "불러오는 중…" : "이전 메시지 보기"}
            </button>
          </li>
        )}
        {isPending && <li className={styles.empty}>불러오는 중…</li>}
        {isError && <li className={styles.empty}>메시지를 불러오지 못했어요.</li>}
        {data && data.items.length === 0 && <li className={styles.empty}>{emptyText}</li>}
        {data?.items.map((message) => (
          <ChatMessageItem
            key={message.id}
            message={message}
            mine={isMine(message, me.username)}
            canDelete={me.can_operate}
            onReply={setReplyTo}
            onDelete={onDelete}
          />
        ))}
      </ul>
      <ChatComposer
        key={room}
        replyTo={replyTo}
        onCancelReply={() => setReplyTo(null)}
        onSend={(body) => send.mutateAsync(body)}
        sending={send.isPending}
        error={send.isError ? errorText(send.error) : remove.isError ? errorText(remove.error) : null}
      />
    </>
  );
}
