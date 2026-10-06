"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SiteFooter() {
  const pathname = usePathname();
  if (pathname === "/map") return null;
  if (pathname === "/login" || pathname === "/signup" || pathname.startsWith("/admin")) {
    return <Link href="/sources" className="fixed bottom-3 right-4 z-10 rounded bg-[var(--bg-base)] px-2 py-1 text-xs text-[var(--text-secondary)] hover:text-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">데이터 출처</Link>;
  }

  return (
    <footer className="mt-auto shrink-0 border-t border-[var(--border)] bg-[var(--bg-base)] px-5 py-4 text-center text-xs leading-6 text-[var(--text-secondary)]">
      공공데이터 출처: 서울 열린데이터광장(공공누리 제1유형), 한국부동산원 R-ONE, 공공데이터포털 외 · {" "}
      <Link href="/sources" className="text-[var(--accent)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">데이터 출처 전체 보기 →</Link>
    </footer>
  );
}
