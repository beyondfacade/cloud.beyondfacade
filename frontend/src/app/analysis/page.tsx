import { Suspense } from "react";
import { AnalysisPage } from "@/features/agent-report/components/analysis-page";

export default function Page() {
  return (
    <Suspense>
      <AnalysisPage />
    </Suspense>
  );
}
