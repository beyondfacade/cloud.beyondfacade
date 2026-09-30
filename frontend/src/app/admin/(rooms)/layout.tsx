import type { Metadata } from "next";
import { Suspense } from "react";
import { AdminShell } from "@/features/admin/components/admin-shell";
import { RouteFallback } from "@/shared/ui/route-fallback";

export const metadata: Metadata = { title: "관제실 — Metabole", robots: { index: false, follow: false } };

export default function AdminRoomsLayout({ children }: LayoutProps<"/admin">) {
  return (
    <Suspense fallback={<RouteFallback label="관제실을 여는 중" />}>
      <AdminShell>{children}</AdminShell>
    </Suspense>
  );
}
