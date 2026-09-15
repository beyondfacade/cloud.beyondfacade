import { Suspense } from "react";
import { AnalysisPage } from "@/features/agent-report/components/analysis-page";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function Page() {
  return (
    <Suspense fallback={<RouteFallback label="분석 화면을 불러오는 중" />}>
      <AnalysisPage />
    </Suspense>
  );
}
