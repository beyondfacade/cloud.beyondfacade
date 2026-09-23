import { Suspense } from "react";
import { PlanPage } from "@/features/plan/components/plan-page";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function Page() {
  return (
    <Suspense fallback={<RouteFallback label="자금 계획 화면을 불러오는 중" />}>
      <PlanPage />
    </Suspense>
  );
}
