"use client";

import { formatClock } from "../lib/format";
import type { Room } from "../lib/rooms";
import { RoomGlyph } from "./room-glyph";
import styles from "./admin.module.css";

interface RoomHeaderProps {
  room: Room;
  updatedAt: number;
  isFetching: boolean;
  isError: boolean;
  onRefresh: () => void;
}

export function RoomHeader({ room, updatedAt, isFetching, isError, onRefresh }: RoomHeaderProps) {
  const state = isError ? "error" : isFetching ? "loading" : "live";
  const liveLabel = isError
    ? "연결 오류"
    : updatedAt
      ? `${formatClock(updatedAt)} 갱신 · ${room.pollMs / 1_000}초마다`
      : "불러오는 중";

  return (
    <header className={styles.roomHeader}>
      <span className={styles.glyph}><RoomGlyph room={room.key} size={34} /></span>
      <div>
        <p className={styles.eyebrow}>{room.badge}</p>
        <div className={styles.roomTitle}>
          <h1>{room.title}</h1>
          <span>{room.titleEn}</span>
        </div>
        <p className={styles.subtitle}>{room.subtitle}</p>
      </div>
      <div className={styles.refresh}>
        <span className={styles.live} role="status" aria-live="polite">
          <span className={styles.liveDot} data-state={state} aria-hidden="true" />
          {liveLabel}
        </span>
        <button type="button" className={styles.ghostButton} onClick={onRefresh} disabled={isFetching}>
          {isFetching ? "갱신 중…" : "지금 새로고침"}
        </button>
      </div>
    </header>
  );
}
