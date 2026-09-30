"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GRADE_LABEL, loginHref, logout, replaceSession, signupHref } from "@/shared/auth/session";
import { useSession } from "@/shared/auth/use-session";
import styles from "./account-menu.module.css";

/** 공개 화면 헤더의 계정 영역 — 비로그인은 로그인·가입, 로그인하면 관리자 페이지(일반은 읽기, 관리자는 쓰기)와 로그아웃. */
export function AccountMenu() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const session = useSession();
  const signOut = useMutation({
    mutationFn: logout,
    onSettled: () => {
      replaceSession(queryClient, null);
      router.refresh();
    },
  });

  if (session.isPending) return <span className={styles.placeholder} aria-hidden="true" />;

  const me = session.data;
  if (!me) {
    return (
      <div className={styles.menu}>
        <Link href={loginHref(pathname)} prefetch={false} className={styles.link}>로그인</Link>
        <Link href={signupHref(pathname)} prefetch={false} className={styles.cta}>회원가입</Link>
      </div>
    );
  }

  return (
    <div className={styles.menu}>
      <Link href="/admin" prefetch={false} className={styles.link} aria-label="관리자 페이지">
        <span className={styles.full}>관리자 페이지</span>
        <span className={styles.short}>관제실</span>
      </Link>
      <span className={styles.who}>
        <span className={styles.name}>{me.username}</span>
        <span className={styles.grade} data-role={me.role}>{GRADE_LABEL[me.role]}</span>
      </span>
      <button type="button" className={styles.link} onClick={() => signOut.mutate()} disabled={signOut.isPending}>
        로그아웃
      </button>
    </div>
  );
}
