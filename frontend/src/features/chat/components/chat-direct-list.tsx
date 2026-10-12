"use client";

import type { ChatRoom } from "@/shared/api/types";
import { badgeLabel, chatTime, lastLine } from "../lib/chat-state";
import styles from "./global-chat.module.css";

const EXPERT_PHOTOS = 6;

/** 전문가 계정의 이력서 사진 — 같은 전문가는 늘 같은 사진. */
export const expertPhoto = (expertId: number) => `/experts/expert-${(expertId % EXPERT_PHOTOS) + 1}.jpg`;

/** 사진이 없으면 기본 사람 모양 아바타. */
export function PersonAvatar({ photo }: { photo?: string }) {
  return (
    <span className={styles.avatar} aria-hidden="true">
      {photo ? (
        <img src={photo} alt="" width={32} height={32} />
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="8.5" r="4" />
          <path d="M4.5 20.5a7.5 7.5 0 0 1 15 0z" />
        </svg>
      )}
    </span>
  );
}

interface Props {
  rooms: ChatRoom[];
  onOpen: (room: ChatRoom) => void;
  /** 1:1은 일반 회원만 전문가에게 건다 — 전문가는 열린 방에서 답만 한다. */
  canStart: boolean;
}

/** 실제로 메시지가 오간 1:1 방 — 최근 대화순. */
export function ChatDirectList({ rooms, onOpen, canStart }: Props) {
  if (rooms.length === 0) {
    return (
      <p className={styles.empty}>
        {canStart ? "아직 대화한 전문가가 없어요." : "아직 1:1 대화가 없어요."}<br />
        {canStart ? "전문가 목록에서 골라 대화를 시작해 보세요." : "1:1 대화는 일반 회원이 전문가에게 걸면 생겨요."}
      </p>
    );
  }
  return (
    <ul className={styles.rows}>
      {rooms.map((room) => {
        const badge = badgeLabel(room.unread);
        return (
          <li key={room.key}>
            <button type="button" className={styles.row} onClick={() => onOpen(room)}>
              <PersonAvatar photo={canStart && room.partner_id !== null ? expertPhoto(room.partner_id) : undefined} />
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
  );
}
