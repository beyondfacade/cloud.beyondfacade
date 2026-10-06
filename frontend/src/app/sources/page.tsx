import type { Metadata } from "next";
import { Suspense } from "react";
import { DataSourcesPage } from "@/features/data-sources/components/data-sources-page";
import { RouteFallback } from "@/shared/ui/route-fallback";

export const metadata: Metadata = { title: "데이터 출처 — Metabole" };

export default function SourcesRoute() {
  return (
    <Suspense fallback={<RouteFallback label="데이터 출처를 불러오는 중" />}>
      <DataSourcesPage />
    </Suspense>
  );
}
