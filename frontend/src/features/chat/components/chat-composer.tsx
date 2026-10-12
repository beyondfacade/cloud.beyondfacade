"use client";

import { type ChangeEvent, type FormEvent, type KeyboardEvent, useRef, useState } from "react";
import type { ChatMessage } from "@/shared/api/types";
import { canSend, MAX_BODY_LENGTH } from "../lib/chat-state";
import styles from "./global-chat.module.css";

interface Props {
  replyTo: ChatMessage | null;
  onCancelReply: () => void;
  onSend: (body: string) => Promise<unknown>;
  sending: boolean;
  error: string | null;
  /** 1:1 대화에서만 — 있으면 PDF 첨부 버튼을 보인다. */
  onAttach?: (file: File) => void;
}

export function ChatComposer({ replyTo, onCancelReply, onSend, sending, error, onAttach }: Props) {
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
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

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // 같은 파일을 다시 골라도 올라가게
    if (file) onAttach?.(file);
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
        {onAttach && (
          <>
            <button
              type="button"
              className={styles.attach}
              aria-label="PDF 첨부"
              title="PDF 첨부 (5MB 이하)"
              onClick={() => fileRef.current?.click()}
              disabled={sending}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 11.5l-8.6 8.6a5 5 0 0 1-7.1-7.1l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9" />
              </svg>
            </button>
            <input ref={fileRef} type="file" accept="application/pdf,.pdf" hidden onChange={onFile} aria-label="PDF 파일" />
          </>
        )}
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
