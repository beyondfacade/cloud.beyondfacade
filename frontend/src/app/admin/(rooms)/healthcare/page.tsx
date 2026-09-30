import { Suspense } from "react";
import { HealthcareRoom } from "@/features/admin/components/healthcare-room";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function HealthcareRoute() {
  return (
    <Suspense fallback={<RouteFallback label="헬스케어실을 불러오는 중" />}>
      <HealthcareRoom />
    </Suspense>
  );
}
