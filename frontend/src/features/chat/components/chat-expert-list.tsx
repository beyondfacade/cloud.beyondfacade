"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import type { ChatRoom } from "@/shared/api/types";
import { CHAT_QUERY_KEY, fetchChatExperts, openDirectRoom } from "../api";
import { initial } from "./chat-direct-list";
import styles from "./global-chat.module.css";

/** 대화할 수 있는 전문가 전체 — 누르면 그 전문가와의 1:1 방을 연다(일반 회원 전용). */
export function ChatExpertList({ onOpen }: { onOpen: (room: ChatRoom) => void }) {
  const experts = useQuery({ queryKey: [...CHAT_QUERY_KEY, "experts"], queryFn: fetchChatExperts });
  const open = useMutation({ mutationFn: openDirectRoom, onSuccess: onOpen });

  if (experts.isPending) return <p className={styles.empty}>전문가 목록을 불러오는 중…</p>;
  if (experts.isError) return <p className={`${styles.empty} ${styles.error}`} role="alert">전문가 목록을 불러오지 못했어요.</p>;
  if (experts.data.length === 0) return <p className={styles.empty}>지금 대화할 수 있는 전문가가 없어요.</p>;
  return (
    <ul className={styles.rows} aria-label="전문가 목록">
      {experts.data.map((peer) => (
        <li key={peer.id}>
          <button type="button" className={styles.row} onClick={() => open.mutate(peer.id)} disabled={open.isPending}>
            <span className={styles.avatar} aria-hidden="true">{initial(peer.username)}</span>
            <span className={styles.rowText}>
              <span className={styles.rowTitle}>{peer.username}</span>
              <span className={styles.rowSub}>대화하기</span>
            </span>
          </button>
        </li>
      ))}
      {open.isError && (
        <li className={`${styles.empty} ${styles.error}`} role="alert">
          {open.error instanceof ApiError ? open.error.message : "대화를 열지 못했어요."}
        </li>
      )}
    </ul>
  );
}
