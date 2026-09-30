import { Suspense } from "react";
import { SecurityRoom } from "@/features/admin/components/security-room";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function SecurityRoute() {
  return (
    <Suspense fallback={<RouteFallback label="보안 감사팀을 불러오는 중" />}>
      <SecurityRoom />
    </Suspense>
  );
}
