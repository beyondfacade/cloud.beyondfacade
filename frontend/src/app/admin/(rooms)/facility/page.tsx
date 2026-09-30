import { Suspense } from "react";
import { FacilityRoom } from "@/features/admin/components/facility-room";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function FacilityRoute() {
  return (
    <Suspense fallback={<RouteFallback label="설비실을 불러오는 중" />}>
      <FacilityRoom />
    </Suspense>
  );
}
