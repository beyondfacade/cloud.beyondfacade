"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "@/shared/api/client";
import { rememberedExpertIndustry } from "@/shared/lib/open-expert-chat";
import type { ChatExpert, ChatExpertStatus, ChatRoom } from "@/shared/api/types";
import { buyConsultation, CHAT_QUERY_KEY, fetchChatExperts, openDirectRoom } from "../api";
import { PersonAvatar } from "./chat-direct-list";
import styles from "./global-chat.module.css";

const EXPERTS_KEY = [...CHAT_QUERY_KEY, "experts"] as const;
const HOURS = [1, 2, 3] as const;
const STATUS_LABEL: Record<ChatExpertStatus, string> = { available: "대화 가능", busy: "대화 중", mine: "내 상담 중" };

const won = (amount: number) => `${amount.toLocaleString("ko-KR")}원`;

/** 기본 순서는 무작위 — 받아 올 때 한 번만 섞어, 보고 있는 동안 줄이 움직이지 않게 한다. */
async function fetchShuffledExperts(): Promise<ChatExpert[]> {
  const experts = [...(await fetchChatExperts())];
  for (let i = experts.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [experts[i], experts[j]] = [experts[j], experts[i]];
  }
  return experts;
}

/** 리포트에서 고른 업종의 전문가를 맨 위로 — 업종 이름이 전문 업종을 품으면 같은 업종(부동산중개업 ⊃ 부동산). */
function industryFirst(experts: ChatExpert[], industry: string | null): ChatExpert[] {
  if (!industry) return experts;
  const matches = (expert: ChatExpert) => !!expert.specialty && industry.includes(expert.specialty);
  return [...experts.filter(matches), ...experts.filter((expert) => !matches(expert))];
}

/** 대화할 수 있는 전문가 전체와 요금·상담 상태 — 상담을 사면 그 전문가와의 1:1 방을 연다(일반 회원 전용). */
export function ChatExpertList({ onOpen }: { onOpen: (room: ChatRoom) => void }) {
  const queryClient = useQueryClient();
  const experts = useQuery({ queryKey: EXPERTS_KEY, queryFn: fetchShuffledExperts, staleTime: 0 });
  const done = (room: ChatRoom) => {
    void queryClient.invalidateQueries({ queryKey: EXPERTS_KEY });
    onOpen(room);
  };
  const open = useMutation({ mutationFn: openDirectRoom, onSuccess: done });
  const buy = useMutation({
    mutationFn: ({ id, hours }: { id: number; hours: number }) => buyConsultation(id, hours),
    onSuccess: done,
  });
  const failed = open.error ?? buy.error;

  if (experts.isPending) return <p className={styles.empty}>전문가 목록을 불러오는 중…</p>;
  if (experts.isError) return <p className={`${styles.empty} ${styles.error}`} role="alert">전문가 목록을 불러오지 못했어요.</p>;
  if (experts.data.length === 0) return <p className={styles.empty}>지금 대화할 수 있는 전문가가 없어요.</p>;
  return (
    <ul className={styles.rows} aria-label="전문가 목록">
      {industryFirst(experts.data, rememberedExpertIndustry()).map((expert) => (
        <ExpertRow
          key={expert.id}
          expert={expert}
          pending={open.isPending || buy.isPending}
          onChat={() => open.mutate(expert.id)}
          onBuy={(hours) => buy.mutate({ id: expert.id, hours })}
        />
      ))}
      {failed && (
        <li className={`${styles.empty} ${styles.error}`} role="alert">
          {failed instanceof ApiError ? failed.message : "대화를 열지 못했어요."}
        </li>
      )}
    </ul>
  );
}

interface RowProps {
  expert: ChatExpert;
  pending: boolean;
  onChat: () => void;
  onBuy: (hours: number) => void;
}

function ExpertRow({ expert, pending, onChat, onBuy }: RowProps) {
  const [hours, setHours] = useState<number>(HOURS[0]);
  const rate = expert.hourly_rate;
  return (
    <li className={styles.expertRow} data-status={expert.status}>
      <PersonAvatar />
      <span className={styles.rowText}>
        <span className={styles.rowTitle}>
          {expert.username}
          {expert.specialty && <span className={styles.specialty}>{expert.specialty} 전문</span>}
        </span>
        <span className={styles.rowSub}>
          {rate === null ? "요금 미정" : `시간당 ${won(rate)}`} · <span className={styles.status}>{STATUS_LABEL[expert.status]}</span>
        </span>
      </span>
      {expert.status === "busy" && <button type="button" className={styles.buy} disabled>대화 중</button>}
      {expert.status === "mine" && <button type="button" className={styles.buy} onClick={onChat} disabled={pending}>대화하기</button>}
      {expert.status === "available" && rate !== null && (
        <span className={styles.buyGroup}>
          <select
            className={styles.hours}
            aria-label={`${expert.username} 상담 시간`}
            value={hours}
            onChange={(event) => setHours(Number(event.target.value))}
          >
            {HOURS.map((h) => <option key={h} value={h}>{h}시간 · {won(rate * h)}</option>)}
          </select>
          <button type="button" className={styles.buy} onClick={() => onBuy(hours)} disabled={pending}>구매</button>
        </span>
      )}
    </li>
  );
}
