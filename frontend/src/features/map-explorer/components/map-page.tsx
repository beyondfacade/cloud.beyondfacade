"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { MapView } from "./map-view";
import { ControlBar } from "./control-bar";
import { SidePanel } from "./side-panel";
import { parseMapState, serializeMapState } from "../lib/map-state";
import type { MapState } from "../lib/map-state";

/** URL 파라미터와 상태를 연동. */
export function MapPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const state = parseMapState(searchParams);

  const handleStateChange = (nextState: MapState) => {
    router.replace(`?${serializeMapState(nextState)}`, { scroll: false });
  };

  const handleSelectRegion = (code: string) => {
    handleStateChange({ ...state, region: code });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ControlBar state={state} onChange={handleStateChange} />
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 overflow-hidden">
          <MapView
            regionCode={state.region}
            metric={state.metric}
            industry={state.industry}
            year={state.year}
            onSelectRegion={handleSelectRegion}
          />
        </div>
        <SidePanel regionCode={state.region} industry={state.industry} />
      </div>
    </div>
  );
}
