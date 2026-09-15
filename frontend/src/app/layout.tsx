import type { Metadata } from "next";
import { ApiProviders } from "@/shared/api/providers";
import { TopBar } from "@/shared/ui/top-bar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Metabole — 상권 분석",
  description: "행정동 단위 상권 지표를 지도에서 탐색하고, AI 에이전트 분석 리포트를 확인합니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" data-theme="light">
      <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.min.css" />
      </head>
      <body className="bg-[var(--bg-base)] text-[var(--text-primary)] min-h-[100dvh] flex flex-col">
        <TopBar />
        <ApiProviders>{children}</ApiProviders>
      </body>
    </html>
  );
}
