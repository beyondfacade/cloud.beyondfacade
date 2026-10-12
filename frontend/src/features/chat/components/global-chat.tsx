"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import type { ChatRoom } from "@/shared/api/types";
import { loginHref, SESSION_QUERY_KEY, signupHref } from "@/shared/auth/session";
import { useSession } from "@/shared/auth/use-session";
import { chatRoomsKey, fetchChatRooms } from "../api";
import { applyChatEvent } from "../hooks/chat-cache";
import { useChatStream } from "../hooks/use-chat-stream";
import { badgeLabel, totalUnread } from "../lib/chat-state";
import { ChatDirectList } from "./chat-direct-list";
import { ChatRoomView } from "./chat-room-view";
import styles from "./global-chat.module.css";

type Tab = "global" | "operators" | "direct";

interface View {
  open: boolean;
  tab: Tab;
  /** owner — 로그아웃 뒤 다른 계정이 이전 사람의 대화방을 이어 열지 않게 */
  dm: { key: string; title: string; owner: string } | null;
}

const STORAGE_KEY = "metabole-chat";
const INITIAL: View = { open: false, tab: "global", dm: null };
// 로그인·가입 화면은 그 자체가 채팅에 들어가는 길이라 띄우지 않는다
const HIDDEN_PATHS = ["/login", "/signup"];
const EMPTY_TEXT: Record<Exclude<Tab, "direct">, string> = {
  global: "아직 대화가 없어요. 첫 인사를 남겨 보세요.",
  operators: "관리자끼리만 보는 방이에요.",
};

/** 탭을 옮겨도(같은 브라우저 탭 안) 창 열림·보던 방을 유지한다. */
function useView() {
  const [view, setView] = useState<View>(() => {
    if (typeof window === "undefined") return INITIAL;
    try {
      return { ...INITIAL, ...JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "{}") };
    } catch {
      return INITIAL;
    }
  });
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(view));
    } catch {
      // 저장소를 못 써도 채팅은 된다
    }
  }, [view]);
  return [view, setView] as const;
}

function BubbleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20.5 11.5a8 8 0 0 1-11.7 7.1L4 20l1.4-4.4a8 8 0 1 1 15.1-4.1z" />
      <path d="M8.6 11.6h.01M12.3 11.6h.01M16 11.6h.01" strokeWidth="2.6" />
    </svg>
  );
}

function CloseIcon({ size = 22 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

function Guest({ next }: { next: string }) {
  return (
    <div className={styles.guest}>
      <p>
        <strong>로그인한 회원만 참여할 수 있어요</strong>
        메타볼레 회원들과 상권 이야기를 나누고,<br />다른 회원과 1:1로 대화할 수 있어요.
      </p>
      <div className={styles.guestLinks}>
        <Link href={loginHref(next)} className={styles.link} data-primary="true">로그인</Link>
        <Link href={signupHref(next)} className={styles.link}>회원가입</Link>
      </div>
    </div>
  );
}

export function GlobalChat() {
  const pathname = usePathname();
  const client = useQueryClient();
  const session = useSession();
  const me = session.data ?? null;
  const [view, setView] = useView();
  const launcherRef = useRef<HTMLButtonElement>(null);
  const rooms = useQuery({ queryKey: chatRoomsKey, queryFn: fetchChatRooms, enabled: me !== null });

  const tab: Tab = view.tab === "operators" && !me?.can_operate ? "global" : view.tab;
  const dm = view.dm && view.dm.owner === me?.username ? view.dm : null;
  const activeRoom = view.open && me ? (tab === "direct" ? (dm?.key ?? null) : tab) : null;

  useChatStream(me !== null, {
    onEvent: (event) => {
      if (me) applyChatEvent(client, event, { me: me.username, activeRoom });
    },
    onLost: () => void client.invalidateQueries({ queryKey: SESSION_QUERY_KEY }),
  });

  if (HIDDEN_PATHS.includes(pathname) || session.isPending) return null;

  const list = rooms.data ?? [];
  const unreadOf = (match: (room: ChatRoom) => boolean) => totalUnread(list.filter(match));
  const tabs: { key: Tab; label: string; unread: number }[] = [
    { key: "global", label: "전체", unread: unreadOf((r) => r.kind === "global") },
    ...(me?.can_operate ? [{ key: "operators" as const, label: "관리자", unread: unreadOf((r) => r.kind === "operators") }] : []),
    { key: "direct", label: "대화", unread: unreadOf((r) => r.kind === "direct") },
  ];
  const badge = badgeLabel(totalUnread(rooms.data));
  const dmTitle = dm && (list.find((r) => r.key === dm.key)?.title ?? dm.title);

  const close = () => {
    setView((v) => ({ ...v, open: false }));
    launcherRef.current?.focus();
  };
  const onPanelKey = (event: KeyboardEvent) => {
    if (event.key === "Escape") close();
  };

  return (
    <>
      <button
        ref={launcherRef}
        type="button"
        className={styles.launcher}
        aria-label={view.open ? "채팅 닫기" : "채팅 열기"}
        aria-expanded={view.open}
        aria-controls="global-chat-panel"
        onClick={() => setView((v) => ({ ...v, open: !v.open }))}
      >
        {view.open ? <CloseIcon /> : <BubbleIcon />}
        {badge && !view.open && <span className={styles.badge} aria-label={`안 읽은 메시지 ${totalUnread(rooms.data)}개`}>{badge}</span>}
      </button>
      {view.open && (
        <section id="global-chat-panel" className={styles.panel} role="dialog" aria-label="메타볼레 채팅" onKeyDown={onPanelKey}>
          <header className={styles.head}>
            <div className={styles.titleRow}>
              <span className={styles.title}>채팅</span>
              {me && <span className={styles.who}>{me.username}</span>}
              <button type="button" className={styles.iconButton} aria-label="채팅창 닫기" onClick={close} style={me ? undefined : { marginLeft: "auto" }}>
                <CloseIcon size={16} />
              </button>
            </div>
            {me && (
              <div role="tablist" aria-label="채팅방" className={styles.tabs}>
                {tabs.map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    role="tab"
                    aria-selected={tab === t.key}
                    className={styles.tab}
                    onClick={() => setView((v) => ({ ...v, tab: t.key, dm: t.key === "direct" && v.tab === "direct" ? null : v.dm }))}
                  >
                    {t.label}
                    {badgeLabel(t.unread) && <span className={styles.count}>{badgeLabel(t.unread)}</span>}
                  </button>
                ))}
              </div>
            )}
          </header>
          <div className={styles.body}>
            {!me && <Guest next={pathname} />}
            {me && tab !== "direct" && <ChatRoomView key={tab} room={tab} me={me} emptyText={EMPTY_TEXT[tab]} />}
            {me && tab === "direct" && dm && (
              <>
                <div className={styles.subHead}>
                  <button type="button" className={styles.iconButton} aria-label="대화 목록으로" onClick={() => setView((v) => ({ ...v, dm: null }))}>
                    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M10 3L5 8l5 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  </button>
                  {dmTitle}
                </div>
                <ChatRoomView key={dm.key} room={dm.key} me={me} emptyText={`${dmTitle}님에게 첫 메시지를 보내 보세요.`} />
              </>
            )}
            {me && tab === "direct" && !dm && (
              <ChatDirectList
                rooms={list.filter((r) => r.kind === "direct")}
                onOpen={(room) => setView((v) => ({ ...v, dm: { key: room.key, title: room.title, owner: me.username } }))}
              />
            )}
          </div>
        </section>
      )}
    </>
  );
}
