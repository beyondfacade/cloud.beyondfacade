"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ApiError } from "@/shared/api/client";
import type { ChatRoom } from "@/shared/api/types";
import { CHAT_QUERY_KEY, openDirectRoom, searchChatMembers } from "../api";
import { badgeLabel, chatTime, lastLine } from "../lib/chat-state";
import styles from "./global-chat.module.css";

const SEARCH_DELAY_MS = 250;

function useDebounced(value: string, delay: number) {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}

const initial = (name: string) => name.slice(0, 1).toUpperCase();

export function ChatDirectList({ rooms, onOpen }: { rooms: ChatRoom[]; onOpen: (room: ChatRoom) => void }) {
  const [q, setQ] = useState("");
  const needle = useDebounced(q.trim(), SEARCH_DELAY_MS);
  const members = useQuery({
    queryKey: [...CHAT_QUERY_KEY, "members", needle],
    queryFn: () => searchChatMembers(needle),
    enabled: needle.length > 0,
  });
  const open = useMutation({ mutationFn: openDirectRoom, onSuccess: onOpen });

  return (
    <>
      <div className={styles.search}>
        <input
          type="search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="회원 이름으로 찾아 새 대화 시작"
          aria-label="대화할 회원 찾기"
          maxLength={50}
        />
      </div>
      <ul className={styles.rows}>
        {needle && (
          <>
            <li className={styles.sectionLabel}>회원 찾기</li>
            {members.data?.length === 0 && <li className={styles.empty}>“{needle}” 회원이 없어요.</li>}
            {members.data?.map((peer) => (
              <li key={peer.id}>
                <button type="button" className={styles.row} onClick={() => open.mutate(peer.id)} disabled={open.isPending}>
                  <span className={styles.avatar} aria-hidden="true">{initial(peer.username)}</span>
                  <span className={styles.rowText}>
                    <span className={styles.rowTitle}>{peer.username}</span>
                    <span className={styles.rowSub}>대화 시작하기</span>
                  </span>
                </button>
              </li>
            ))}
            {open.isError && (
              <li className={`${styles.empty} ${styles.error}`} role="alert">
                {open.error instanceof ApiError ? open.error.message : "대화를 열지 못했어요."}
              </li>
            )}
            <li className={styles.sectionLabel}>내 대화</li>
          </>
        )}
        {rooms.length === 0 && (
          <li className={styles.empty}>아직 1:1 대화가 없어요.<br />위에서 회원을 찾아 대화를 시작해 보세요.</li>
        )}
        {rooms.map((room) => {
          const badge = badgeLabel(room.unread);
          return (
            <li key={room.key}>
              <button type="button" className={styles.row} onClick={() => onOpen(room)}>
                <span className={styles.avatar} aria-hidden="true">{initial(room.title)}</span>
                <span className={styles.rowText}>
                  <span className={styles.rowTitle}>{room.title}</span>
                  <span className={styles.rowSub}>{lastLine(room.last_message)}</span>
                </span>
                <span className={styles.rowSide}>
                  {room.last_message && <time dateTime={room.last_message.created_at}>{chatTime(room.last_message.created_at)}</time>}
                  {badge && <span className={styles.count} aria-label={`안 읽은 메시지 ${room.unread}개`}>{badge}</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}
