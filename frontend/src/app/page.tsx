import { Suspense } from "react";
import { MapPage } from "@/features/map-explorer/components/map-page";

export default function Home() {
  return (
    <Suspense>
      <MapPage />
    </Suspense>
  );
}
