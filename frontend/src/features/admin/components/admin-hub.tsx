import Link from "next/link";
import { ROOMS } from "../lib/rooms";
import { RoomGlyph } from "./room-glyph";
import styles from "./admin.module.css";

export function AdminHub() {
  return (
    <>
      <section className={styles.hubHero}>
        <p className={styles.eyebrow}>METABOLE CONTROL ROOM</p>
        <h1>
          Metabole을 <em>지키는</em> 세 개의 방
        </h1>
        <p>접근 이상 징후, AI 분석 파이프라인, 서버와 수집기 상태를 방마다 실데이터로 점검합니다.</p>
      </section>
      <nav className={styles.doors} aria-label="관리자 방 입구">
        {ROOMS.map((room) => (
          <Link key={room.key} href={room.href} className={styles.door} prefetch={false}>
            <span className={styles.eyebrow}>{room.badge}</span>
            <RoomGlyph room={room.key} size={36} />
            <h2>
              {room.title}
              <span>{room.titleEn}</span>
            </h2>
            <p>{room.subtitle}</p>
            <span className={styles.doorArrow}>
              입장하기
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8h10m-4-4 4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </span>
          </Link>
        ))}
      </nav>
    </>
  );
}
