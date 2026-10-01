"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AccountMenu } from "./account-menu";
import { ThemeToggle } from "./theme-toggle";
import styles from "./top-bar.module.css";

const TABS = [
  { href: "/map", label: "경고 지도" },
  { href: "/analysis", label: "리포트" },
];

// 첫 화면·관제실·로그인/가입은 자체 헤더를 쓴다
const OWN_HEADER = ["/admin", "/login", "/signup"];

export function TopBar() {
  const pathname = usePathname();
  if (pathname === "/" || OWN_HEADER.some((prefix) => pathname.startsWith(prefix))) return null;

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/" className={styles.brand} aria-label="Metabole">
          <span className={styles.mark} aria-hidden="true">m.</span>
          <span className={styles.wordmark}>Metabole<small>서울 상권 메타볼레</small></span>
        </Link>
        <nav className={styles.navigation} aria-label="주요 메뉴">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                prefetch={false}
                aria-current={active ? "page" : undefined}
                className={styles.tab}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
        <div className={styles.side}>
          <AccountMenu />
          <div className={styles.theme}><ThemeToggle /></div>
        </div>
      </div>
    </header>
  );
}
