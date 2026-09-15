import { Suspense } from "react";
import { MapPage } from "@/features/map-explorer/components/map-page";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function Home() {
  return (
    <Suspense fallback={<RouteFallback label="지도를 불러오는 중" />}>
      <MapPage />
    </Suspense>
  );
}
