"use client";

import { type FormEvent, type KeyboardEvent, useState } from "react";
import type { ChatMessage } from "@/shared/api/types";
import { canSend, MAX_BODY_LENGTH } from "../lib/chat-state";
import styles from "./global-chat.module.css";

interface Props {
  replyTo: ChatMessage | null;
  onCancelReply: () => void;
  onSend: (body: string) => Promise<unknown>;
  sending: boolean;
  error: string | null;
}

export function ChatComposer({ replyTo, onCancelReply, onSend, sending, error }: Props) {
  const [text, setText] = useState("");
  const length = text.trim().length;
  const ready = canSend(text) && !sending;

  const submit = async () => {
    if (!ready) return;
    try {
      await onSend(text);
      setText("");
    } catch {
      // 오류 문구는 상위가 보여 준다 — 쓰던 글은 남긴다
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // 한글 조합 중 Enter는 글자 확정이지 보내기가 아니다
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void submit();
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void submit();
  };

  return (
    <form className={styles.composer} onSubmit={onSubmit}>
      {replyTo && (
        <div className={styles.replyBar}>
          <span className={styles.replyText}>
            <b>{replyTo.sender_username}</b>에게 답장 · {(replyTo.body ?? "").split("\n")[0]}
          </span>
          <button type="button" className={styles.iconButton} aria-label="답장 취소" onClick={onCancelReply}>
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
        </div>
      )}
      <div className={styles.inputRow}>
        <textarea
          className={styles.input}
          rows={1}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="메시지를 입력하세요"
          aria-label="메시지 입력"
        />
        <button type="submit" className={styles.send} disabled={!ready}>보내기</button>
      </div>
      <div className={styles.foot}>
        <span className={error ? styles.error : undefined} role={error ? "alert" : undefined}>
          {error ?? "Enter 보내기 · Shift+Enter 줄바꿈"}
        </span>
        <span data-over={length > MAX_BODY_LENGTH}>{length}/{MAX_BODY_LENGTH}</span>
      </div>
    </form>
  );
}
