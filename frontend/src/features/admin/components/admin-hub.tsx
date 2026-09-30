"use client";

import Link from "next/link";
import type { AdminUserFilter } from "@/shared/api/types";
import { fetchAdminUsers, fetchFacilitySnapshot, fetchHealthcareSnapshot, fetchSecurityOverview } from "../api";
import { useAdminQuery } from "../hooks/use-admin-query";
import { facilityStatus, healthcareStatus, securityStatus, usersStatus, type DoorStatus } from "../lib/hub-status";
import { ROOMS, type RoomKey } from "../lib/rooms";
import { Badge } from "./admin-ui";
import { RoomGlyph } from "./room-glyph";
import styles from "./admin.module.css";

const HUB_POLL_MS = 60_000;
const EVERYONE: AdminUserFilter = { q: "", role: null, status: "all" };

/** 방 스냅샷과 같은 쿼리 키 — 문을 열고 들어가면 캐시를 그대로 이어 쓴다. */
function useDoorStatuses(): Record<RoomKey, DoorStatus | null> {
  const security = useAdminQuery(["admin", "security", "overview"], fetchSecurityOverview, HUB_POLL_MS);
  const healthcare = useAdminQuery(["admin", "healthcare", "snapshot"], fetchHealthcareSnapshot, HUB_POLL_MS);
  const facility = useAdminQuery(["admin", "facility", "snapshot"], fetchFacilitySnapshot, HUB_POLL_MS);
  const users = useAdminQuery(["admin", "users", EVERYONE], () => fetchAdminUsers(EVERYONE), HUB_POLL_MS);
  const unreachable: DoorStatus = { tone: "danger", label: "상태 확인 실패" };
  const pick = <T,>(q: { data?: T; isError: boolean }, status: (data: T) => DoorStatus) =>
    q.data ? status(q.data) : q.isError ? unreachable : null;
  return {
    security: pick(security, securityStatus),
    healthcare: pick(healthcare, healthcareStatus),
    facility: pick(facility, facilityStatus),
    users: pick(users, (d) => usersStatus(d.items)),
  };
}

export function AdminHub() {
  const statuses = useDoorStatuses();
  return (
    <>
      <section className={styles.hubHero}>
        <p className={styles.eyebrow}>METABOLE CONTROL ROOM</p>
        <h1>
          Metabole을 <em>지키는</em> 네 개의 방
        </h1>
        <p>접근 이상 징후, AI 분석 파이프라인, 서버와 수집기 상태, 관리자 계정을 방마다 실데이터로 점검합니다.</p>
      </section>
      <nav className={styles.doors} aria-label="관리자 방 입구">
        {ROOMS.map((room) => {
          const status = statuses[room.key];
          return (
            <Link key={room.key} href={room.href} className={styles.door} prefetch={false}>
              <span className={styles.eyebrow}>{room.badge}</span>
              <RoomGlyph room={room.key} size={36} />
              <h2>
                {room.title}
                <span>{room.titleEn}</span>
              </h2>
              <span className={styles.doorStatus} aria-live="polite">
                {status ? <Badge tone={status.tone} dot>{status.label}</Badge> : <Badge>확인 중…</Badge>}
              </span>
              <p>{room.subtitle}</p>
              <span className={styles.doorArrow}>
                입장하기
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8h10m-4-4 4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
