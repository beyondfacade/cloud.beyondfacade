import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./auth.module.css";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className={styles.page}>
      <aside className={styles.aside}>
        <Link href="/" className={styles.brand} aria-label="Metabole 첫 화면">
          Metabole
          <small>SEOUL COMMERCIAL METABOLE</small>
        </Link>
        <p className={styles.tagline}>
          서울 상권 메타볼레 계정 하나로 지도 탐색과 AI 분석, 관제실을 함께 이용합니다.
        </p>
      </aside>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
