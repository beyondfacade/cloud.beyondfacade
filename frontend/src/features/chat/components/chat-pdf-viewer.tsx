"use client";

import { useQuery } from "@tanstack/react-query";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { ChatMessage } from "@/shared/api/types";
import { CHAT_QUERY_KEY, fetchChatAttachment } from "../api";
import styles from "./global-chat.module.css";

/** 첨부 PDF를 화면 가득 — 로그인 쿠키로 받아 blob URL로 띄우므로 API가 다른 origin이어도 된다. */
export function ChatPdfViewer({ message, onClose }: { message: ChatMessage; onClose: () => void }) {
  const name = message.attachment?.name ?? "PDF";
  const closeRef = useRef<HTMLButtonElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  const pdf = useQuery({
    queryKey: [...CHAT_QUERY_KEY, "attachment", message.id],
    queryFn: () => fetchChatAttachment(message.id),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (!pdf.data) return;
    const objectUrl = URL.createObjectURL(pdf.data);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [pdf.data]);

  useEffect(() => closeRef.current?.focus(), []);

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "Escape") return;
    event.stopPropagation(); // 채팅 창까지 닫지 않는다
    onClose();
  };

  return createPortal(
    <div className={styles.viewerBackdrop} onClick={onClose}>
      <section
        className={styles.viewer}
        role="dialog"
        aria-modal="true"
        aria-label={`${name} 보기`}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <header className={styles.viewerHead}>
          <span className={styles.viewerTitle}>{name}</span>
          {url && (
            <a className={styles.viewerLink} href={url} download={name}>내려받기</a>
          )}
          <button ref={closeRef} type="button" className={styles.iconButton} aria-label="PDF 닫기" onClick={onClose}>
            <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
        </header>
        {pdf.isError && <p className={styles.empty}>PDF를 불러오지 못했어요.</p>}
        {!pdf.isError && !url && <p className={styles.empty}>불러오는 중…</p>}
        {url && <iframe className={styles.viewerFrame} src={url} title={name} />}
      </section>
    </div>,
    document.body,
  );
}
