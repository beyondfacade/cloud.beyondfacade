"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MapView } from "./map-view";
import { ControlBar } from "./control-bar";
import { SidePanel } from "./side-panel";
import { parseMapState, serializeMapState } from "../lib/map-state";
import type { MapState } from "../lib/map-state";
import styles from "./map-workspace.module.css";

/** URL 파라미터와 상태를 연동. */
export function MapPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const state = parseMapState(searchParams);
  // 폐업 마커 토글 — URL·localStorage에 넣지 않는다 (설계서 §6-2), 기본 꺼짐.
  const [showClosed, setShowClosed] = useState(false);

  const handleStateChange = (nextState: MapState) => {
    router.replace(`?${serializeMapState(nextState)}`, { scroll: false });
  };

  const handleSelectRegion = (code: string) => {
    handleStateChange({ ...state, region: code });
  };

  return (
    <main className={styles.workspace}>
      <header className={styles.pageHeading}>
        <div>
          <p className={styles.eyebrow}>EXPLORE THE NEIGHBORHOOD</p>
          <h1>피해야 할 동네부터 보입니다.</h1>
        </div>
        <p className={styles.pageDescription}>업종을 고르면 서울 427개 동의 창업 경고가 색으로 나타납니다.<br />동을 누르면 근거와 대안이 나옵니다.</p>
      </header>
      <ControlBar state={state} onChange={handleStateChange} />
      <div className={styles.mapAndBrief}>
        <section className={styles.mapSurface} aria-label="서울 상권 지도">
          <div className={styles.mapCaption}><span><span className={styles.locationDot} aria-hidden="true" />서울특별시</span><span>{state.region ? "상점 위치 · 현재 자료" : "행정동 단위 · 지도에서 동네 선택"}</span></div>
          <div className={styles.mapCanvas}>
            <MapView
              regionCode={state.region}
              industry={state.industry}
              onSelectRegion={handleSelectRegion}
              showClosed={showClosed}
            />
          </div>
        </section>
        <SidePanel
          regionCode={state.region}
          industry={state.industry}
          budget={state.budget}
          showClosed={showClosed}
          onToggleClosed={setShowClosed}
        />
      </div>
    </main>
  );
}
