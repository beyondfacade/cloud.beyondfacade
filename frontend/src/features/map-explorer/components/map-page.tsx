"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MapView } from "./map-view";
import { ControlBar } from "./control-bar";
import { SidePanel } from "./side-panel";
import { parseMapState, serializeMapState } from "../lib/map-state";
import { clampToCoverage } from "../lib/metric-coverage";
import type { MapState } from "../lib/map-state";
import styles from "./map-workspace.module.css";

/** URL 파라미터와 상태를 연동. */
export function MapPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // URL로 직접 들어온 조합도 보정한다 — 예: ?industry=childcare&metric=store_count&year=2020
  const state = clampToCoverage(parseMapState(searchParams));
  const canonical = serializeMapState(state);

  // 보정이 실제로 값을 바꿨으면 URL도 맞춘다. clamp가 멱등이라 한 번 바꾸면 다시 걸리지 않는다.
  useEffect(() => {
    if (searchParams.toString() !== canonical) router.replace(`?${canonical}`, { scroll: false });
  }, [searchParams, canonical, router]);

  const handleStateChange = (nextState: MapState) => {
    router.replace(`?${serializeMapState(clampToCoverage(nextState))}`, { scroll: false });
  };

  const handleSelectRegion = (code: string) => {
    handleStateChange({ ...state, region: code });
  };

  return (
    <main className={styles.workspace}>
      <header className={styles.pageHeading}>
        <div>
          <p className={styles.eyebrow}>EXPLORE THE NEIGHBORHOOD</p>
          <h1>동네의 가능성을 펼쳐보세요.</h1>
        </div>
        <p className={styles.pageDescription}>궁금한 동네를 선택하고,<br />상권의 흐름을 차근차근 살펴보세요.</p>
      </header>
      <ControlBar state={state} onChange={handleStateChange} />
      <div className={styles.mapAndBrief}>
        <section className={styles.mapSurface} aria-label="서울 상권 지도">
          <div className={styles.mapCaption}><span><span className={styles.locationDot} aria-hidden="true" />서울특별시</span><span>행정동 단위 · 지도에서 동네 선택</span></div>
          <div className={styles.mapCanvas}>
            <MapView
              regionCode={state.region}
              metric={state.metric}
              industry={state.industry}
              year={state.year}
              yearQuarter={state.year_quarter}
              onSelectRegion={handleSelectRegion}
            />
          </div>
        </section>
        <SidePanel regionCode={state.region} industry={state.industry} budget={state.budget} />
      </div>
    </main>
  );
}
