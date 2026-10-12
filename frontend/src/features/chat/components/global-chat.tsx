"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import type { ChatRoom } from "@/shared/api/types";
import { loginHref, SESSION_QUERY_KEY, signupHref } from "@/shared/auth/session";
import { useSession } from "@/shared/auth/use-session";
import { EXPERT_CHAT_EVENT } from "@/shared/lib/open-expert-chat";
import { chatRoomsKey, fetchChatExperts, fetchChatRooms } from "../api";
import { applyChatEvent } from "../hooks/chat-cache";
import { useChatStream } from "../hooks/use-chat-stream";
import { badgeLabel, totalUnread } from "../lib/chat-state";
import { ChatDirectList } from "./chat-direct-list";
import { ChatExpertList } from "./chat-expert-list";
import { ChatRoomView } from "./chat-room-view";
import styles from "./global-chat.module.css";

type Mode = "global" | "direct";
type GlobalRoom = "global" | "operators";
type DirectView = "experts" | "rooms";

interface View {
  open: boolean;
  mode: Mode;
  room: GlobalRoom;
  directView: DirectView;
  /** owner — 로그아웃 뒤 다른 계정이 이전 사람의 대화방을 이어 열지 않게 */
  dm: { key: string; title: string; owner: string } | null;
}

const STORAGE_KEY = "metabole-chat-v2";
const INITIAL: View = { open: false, mode: "global", room: "global", directView: "rooms", dm: null };
// 로그인·가입 화면은 그 자체가 채팅에 들어가는 길이라 띄우지 않는다
const HIDDEN_PATHS = ["/login", "/signup"];
const MODES: { key: Mode; label: string }[] = [
  { key: "global", label: "글로벌 채팅" },
  { key: "direct", label: "DM" },
];
const GLOBAL_ROOMS: { key: GlobalRoom; label: string }[] = [
  { key: "global", label: "전체" },
  { key: "operators", label: "관리자" },
];
const DIRECT_VIEWS: { key: DirectView; label: string }[] = [
  { key: "experts", label: "전문가 목록" },
  { key: "rooms", label: "대화한 전문가" },
];
const EMPTY_TEXT: Record<GlobalRoom, string> = {
  global: "아직 대화가 없어요. 첫 인사를 남겨 보세요.",
  operators: "관리자끼리만 보는 방이에요.",
};

const withUnread = (label: string, unread: number) => (unread > 0 ? `${label} (${badgeLabel(unread)})` : label);

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
        메타볼레 회원들과 상권 이야기를 나누고,<br />전문가와 1:1로 대화할 수 있어요.
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

  const room: GlobalRoom = view.room === "operators" && !me?.can_operate ? "global" : view.room;
  const canStart = me?.role === "viewer";
  const directView: DirectView = canStart ? view.directView : "rooms";
  const dm = view.dm && view.dm.owner === me?.username ? view.dm : null;
  const activeRoom = view.open && me ? (view.mode === "direct" ? (dm?.key ?? null) : room) : null;

  useChatStream(me !== null, {
    onEvent: (event) => {
      if (me) applyChatEvent(client, event, { me: me.username, activeRoom });
    },
    onLost: () => void client.invalidateQueries({ queryKey: SESSION_QUERY_KEY }),
  });

  useEffect(() => {
    // 비로그인은 열린 창의 로그인 안내를, 일반 회원이 아니면 DM 대화 목록을 본다
    const onExpert = () => setView((v) => ({ ...v, open: true, mode: "direct", directView: "experts", dm: null }));
    window.addEventListener(EXPERT_CHAT_EVENT, onExpert);
    return () => window.removeEventListener(EXPERT_CHAT_EVENT, onExpert);
  }, [setView]);

  if (HIDDEN_PATHS.includes(pathname) || session.isPending) return null;

  const list = rooms.data ?? [];
  const unreadOf = (match: (room: ChatRoom) => boolean) => totalUnread(list.filter(match));
  const directRooms = list.filter((r) => r.kind === "direct");
  const modeUnread: Record<Mode, number> = { global: unreadOf((r) => r.kind !== "direct"), direct: totalUnread(directRooms) };
  const badge = badgeLabel(totalUnread(rooms.data));
  const dmTitle = dm && (list.find((r) => r.key === dm.key)?.title ?? dm.title);
  const openDm = (opened: ChatRoom) =>
    setView((v) => ({ ...v, dm: { key: opened.key, title: opened.title, owner: me!.username } }));
  // 일반 회원이 DM을 누르면: 대화한 방이 있고 지금 시간을 산 전문가가 있으면 대화한 전문가, 아니면 전문가 목록
  const pickDirectView = async (): Promise<DirectView> => {
    if (directRooms.length === 0) return "experts";
    try {
      const experts = await fetchChatExperts();
      return experts.some((expert) => expert.status === "mine") ? "rooms" : "experts";
    } catch {
      return "experts";
    }
  };
  const selectMode = async (mode: Mode) => {
    const picked = mode === "direct" && canStart ? await pickDirectView() : null;
    setView((v) => ({
      ...v, mode, directView: picked ?? v.directView, dm: mode === "direct" && v.mode === "direct" ? null : v.dm,
    }));
  };

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
              <div className={styles.modeRow}>
                <div role="tablist" aria-label="채팅 종류" className={styles.toggle}>
                  {MODES.map((m) => (
                    <button
                      key={m.key}
                      type="button"
                      role="tab"
                      aria-selected={view.mode === m.key}
                      className={styles.toggleButton}
                      onClick={() => void selectMode(m.key)}
                    >
                      {m.label}
                      {badgeLabel(modeUnread[m.key]) && <span className={styles.count}>{badgeLabel(modeUnread[m.key])}</span>}
                    </button>
                  ))}
                </div>
                {view.mode === "global" && me.can_operate && (
                  <select
                    className={styles.select}
                    aria-label="글로벌 채팅방"
                    value={room}
                    onChange={(e) => setView((v) => ({ ...v, room: e.target.value as GlobalRoom }))}
                  >
                    {GLOBAL_ROOMS.map((r) => (
                      <option key={r.key} value={r.key}>{withUnread(r.label, unreadOf((x) => x.kind === r.key))}</option>
                    ))}
                  </select>
                )}
                {view.mode === "direct" && canStart && !dm && (
                  <select
                    className={styles.select}
                    aria-label="DM 보기"
                    value={directView}
                    onChange={(e) => setView((v) => ({ ...v, directView: e.target.value as DirectView }))}
                  >
                    {DIRECT_VIEWS.map((d) => (
                      <option key={d.key} value={d.key}>{withUnread(d.label, d.key === "rooms" ? modeUnread.direct : 0)}</option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </header>
          <div className={styles.body}>
            {!me && <Guest next={pathname} />}
            {me && view.mode === "global" && <ChatRoomView key={room} room={room} me={me} emptyText={EMPTY_TEXT[room]} />}
            {me && view.mode === "direct" && dm && (
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
            {me && view.mode === "direct" && !dm && directView === "experts" && <ChatExpertList onOpen={openDm} />}
            {me && view.mode === "direct" && !dm && directView === "rooms" && (
              <ChatDirectList rooms={directRooms} canStart={canStart} onOpen={openDm} />
            )}
          </div>
        </section>
      )}
    </>
  );
}
