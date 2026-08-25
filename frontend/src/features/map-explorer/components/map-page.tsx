"use client";

import { useState } from "react";
import { MapView } from "./map-view";
import type { MetricKey } from "@/shared/api/types";

const DEFAULT_INDUSTRY = "cafe";
const DEFAULT_METRIC: MetricKey = "closure_rate";
const DEFAULT_YEAR = 2026;

/** URL 파라미터 연동은 Task 6·7에서 확장. 현재는 기본값 + 선택 상태만 보관. */
export function MapPage() {
  const [regionCode, setRegionCode] = useState<string | null>(null);

  return (
    <div className="flex flex-1 flex-col">
      <MapView
        regionCode={regionCode}
        metric={DEFAULT_METRIC}
        industry={DEFAULT_INDUSTRY}
        year={DEFAULT_YEAR}
        onSelectRegion={setRegionCode}
      />
    </div>
  );
}
