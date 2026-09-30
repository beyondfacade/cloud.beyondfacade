"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { loginAdmin } from "../api";
import { safeAdminNext } from "../lib/rooms";
import styles from "./admin.module.css";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const login = useMutation({
    mutationFn: () => loginAdmin(username.trim(), password),
    onSuccess: (me) => {
      queryClient.setQueryData(["admin", "me"], me);
      router.replace(safeAdminNext(searchParams.get("next")));
    },
    onError: () => setPassword(""),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!username.trim() || !password) return;
    login.mutate();
  }

  return (
    <div className={styles.loginPage}>
      <aside className={styles.loginAside}>
        <p className={styles.loginBrand}>
          Metabole
          <small>CONTROL ROOM</small>
        </p>
        <p className={styles.loginTagline}>
          서울 상권 분석 서비스의 보안·AI 파이프라인·설비를 한 곳에서 지켜보는 관리자 관제실입니다.
        </p>
      </aside>
      <main className={styles.loginMain}>
        <form className={styles.loginForm} onSubmit={onSubmit} aria-label="관리자 로그인">
          <h1>관리자 로그인</h1>
          <p className={styles.loginLead}>발급받은 관리자 계정으로 들어오세요.</p>
          <label className={styles.field}>
            아이디
            <input
              className={styles.input}
              name="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className={styles.field}>
            비밀번호
            <input
              className={styles.input}
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {login.isError && (
            <p className={styles.formError} role="alert">
              {login.error instanceof Error ? login.error.message : "로그인에 실패했습니다."}
            </p>
          )}
          <button type="submit" className={styles.primaryButton} disabled={login.isPending}>
            {login.isPending ? "확인 중…" : "들어가기"}
          </button>
        </form>
      </main>
    </div>
  );
}
