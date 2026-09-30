import { Suspense } from "react";
import { SupportPage } from "@/features/support/components/support-page";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function Page() {
  return (
    <Suspense fallback={<RouteFallback label="창업 지원 정보를 불러오는 중" />}>
      <SupportPage />
    </Suspense>
  );
}
