import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/features/admin/components/login-form";
import { RouteFallback } from "@/shared/ui/route-fallback";

export const metadata: Metadata = { title: "관리자 로그인 — Metabole", robots: { index: false, follow: false } };

export default function AdminLoginRoute() {
  return (
    <Suspense fallback={<RouteFallback label="로그인 화면을 불러오는 중" />}>
      <LoginForm />
    </Suspense>
  );
}
