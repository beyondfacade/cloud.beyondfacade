"use client";

import type { ChatMessage } from "@/shared/api/types";
import { chatTime } from "../lib/chat-state";
import { PersonAvatar, profilePhoto } from "./chat-direct-list";
import styles from "./global-chat.module.css";

interface Props {
  message: ChatMessage;
  mine: boolean;
  canDelete: boolean;
  onReply: (message: ChatMessage) => void;
  onDelete: (message: ChatMessage) => void;
  onOpenPdf: (message: ChatMessage) => void;
}

const fileSize = (bytes: number) =>
  bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))}KB` : `${(bytes / 1024 / 1024).toFixed(1)}MB`;

export function ChatMessageItem({ message, mine, canDelete, onReply, onDelete, onOpenPdf }: Props) {
  const quote = message.reply_to;
  const file = message.deleted ? null : message.attachment;
  const senderPhoto =
    message.sender_id !== null
      ? profilePhoto(message.sender_id, message.sender_avatar_version, message.sender_role === "expert")
      : undefined;
  return (
    <li className={styles.message} data-mine={mine} data-deleted={message.deleted}>
      {!mine && <PersonAvatar photo={senderPhoto} />}
      <div className={styles.messageBody}>
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
        {file ? (
          <button type="button" className={styles.fileCard} onClick={() => onOpenPdf(message)} aria-label={`${file.name} PDF 크게 보기`}>
            <span className={styles.fileBadge} aria-hidden="true">PDF</span>
            <span className={styles.fileText}>
              <span className={styles.fileName}>{file.name}</span>
              <span className={styles.fileSize}>{fileSize(file.size)} · 눌러서 크게 보기</span>
            </span>
          </button>
        ) : (
          <p className={styles.bubble}>{message.deleted ? "삭제된 메시지입니다" : message.body}</p>
        )}
        {!message.deleted && (
          <div className={styles.actions}>
            <button type="button" className={styles.action} onClick={() => onReply(message)}>답장</button>
            {canDelete && (
              <button type="button" className={styles.action} data-danger="true" onClick={() => onDelete(message)}>삭제</button>
            )}
          </div>
        )}
      </div>
    </li>
  );
}
