"use client";

import { useSearchParams } from "next/navigation";
import { AnalysisForm } from "./analysis-form";
import { ProgressPanel } from "./progress-panel";
import { ReportView } from "./report-view";
import { useAgentReport } from "../hooks/use-agent-report";

/** URL region·industry 프리필 → 분석 시작 → 진행 패널(좌) + 리포트(우). */
export function AnalysisPage() {
  const searchParams = useSearchParams();
  const { state, start } = useAgentReport();

  return (
    <div className="flex flex-1 flex-col gap-4 p-4">
      <AnalysisForm
        initialRegion={searchParams.get("region") ?? ""}
        initialIndustry={searchParams.get("industry") ?? ""}
        onSubmit={start}
      />
      {state.error && <p className="text-sm text-[var(--danger)]">{state.error}</p>}
      <div className="flex flex-1 gap-4">
        <div className="w-80 shrink-0">
          <ProgressPanel state={state} />
        </div>
        <div className="min-w-0 flex-1">
          <ReportView state={state} />
        </div>
      </div>
    </div>
  );
}
