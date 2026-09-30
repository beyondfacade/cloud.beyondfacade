import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { LoginForm } from "@/features/auth/components/login-form";
import { RouteFallback } from "@/shared/ui/route-fallback";

export const metadata: Metadata = { title: "로그인 — Metabole", robots: { index: false, follow: false } };

export default function LoginRoute() {
  return (
    <AuthLayout>
      <Suspense fallback={<RouteFallback label="로그인 화면을 불러오는 중" />}>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
