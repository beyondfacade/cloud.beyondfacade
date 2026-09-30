import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { SignupForm } from "@/features/auth/components/signup-form";
import { RouteFallback } from "@/shared/ui/route-fallback";

export const metadata: Metadata = { title: "회원가입 — Metabole", robots: { index: false, follow: false } };

export default function SignupRoute() {
  return (
    <AuthLayout>
      <Suspense fallback={<RouteFallback label="가입 화면을 불러오는 중" />}>
        <SignupForm />
      </Suspense>
    </AuthLayout>
  );
}
