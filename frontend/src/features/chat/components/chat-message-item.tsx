"use client";

import type { ChatMessage } from "@/shared/api/types";
import { chatTime } from "../lib/chat-state";
import styles from "./global-chat.module.css";

interface Props {
  message: ChatMessage;
  mine: boolean;
  canDelete: boolean;
  onReply: (message: ChatMessage) => void;
  onDelete: (message: ChatMessage) => void;
}

export function ChatMessageItem({ message, mine, canDelete, onReply, onDelete }: Props) {
  const quote = message.reply_to;
  return (
    <li className={styles.message} data-mine={mine} data-deleted={message.deleted}>
      <div className={styles.meta}>
        {!mine && <span className={styles.name}>{message.sender_username}</span>}
        {message.sender_role === "operator" && <span className={styles.grade}>관리자</span>}
        <time dateTime={message.created_at}>{chatTime(message.created_at)}</time>
      </div>
      {quote && (
        <div className={styles.quote}>
          {quote.sender_username}에게 답장 · {quote.deleted ? "삭제된 메시지" : quote.preview}
        </div>
      )}
      <p className={styles.bubble}>{message.deleted ? "삭제된 메시지입니다" : message.body}</p>
      {!message.deleted && (
        <div className={styles.actions}>
          <button type="button" className={styles.action} onClick={() => onReply(message)}>답장</button>
          {canDelete && (
            <button type="button" className={styles.action} data-danger="true" onClick={() => onDelete(message)}>삭제</button>
          )}
        </div>
      )}
    </li>
  );
}
