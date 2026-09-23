import type { Metadata } from "next";
import { ApiProviders } from "@/shared/api/providers";
import { TopBar } from "@/shared/ui/top-bar";
// Pretendard 셀프호스팅 — globals.css의 @import는 Tailwind v4 리졸버가 패키지 경로를 못 풀어 500이 난다.
// App Router 레이아웃의 JS import는 Next가 직접 처리하고, 상대 url()의 woff2도 정적 자산으로 옮긴다.
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Metabole — 상권 분석",
  description: "행정동 단위 상권 지표를 지도에서 탐색하고, AI 에이전트 분석 리포트를 확인합니다.",
};

const THEME_BOOT =
  "(function(){try{var t=localStorage.getItem('metabole-theme');if(t==='dark'||t==='light')document.documentElement.dataset.theme=t;}catch(e){}})();";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body className="bg-[var(--bg-base)] text-[var(--text-primary)] min-h-[100dvh] flex flex-col">
        <TopBar />
        <ApiProviders>{children}</ApiProviders>
      </body>
    </html>
  );
}
