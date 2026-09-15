"use client";

import { useSearchParams } from "next/navigation";
import { AnalysisForm } from "./analysis-form";
import { ProgressPanel } from "./progress-panel";
import { ReportView } from "./report-view";
import { useAgentReport } from "../hooks/use-agent-report";

/** URL region·industry 프리필 → 분석 시작 → 진행 패널(좌) + 리포트(우). */
export function AnalysisPage() {
  const searchParams = useSearchParams();
  const { state, start, loading } = useAgentReport();

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-1 flex-col gap-8 px-6 py-8">
      <div className="max-w-xl">
        <AnalysisForm
          initialRegion={searchParams.get("region") ?? ""}
          initialIndustry={searchParams.get("industry") ?? ""}
          onSubmit={start}
          disabled={loading}
        />
        {state.error && (
          <p role="alert" className="mt-3 text-sm text-[var(--danger)]">
            {state.error}
          </p>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-8 lg:flex-row lg:gap-10">
        <div className="w-full shrink-0 lg:w-72">
          <ProgressPanel state={state} />
        </div>
        <div className="min-w-0 flex-1">
          <ReportView state={state} />
        </div>
      </div>
    </div>
  );
}
