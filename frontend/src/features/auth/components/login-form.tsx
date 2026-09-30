"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { replaceSession, safeNext, signupHref } from "@/shared/auth/session";
import { login } from "../api";
import { redirectErrorMessage } from "../lib/auth-errors";
import { GoogleButton } from "./google-button";
import styles from "./auth.module.css";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const next = safeNext(searchParams.get("next"));
  const redirectError = redirectErrorMessage(searchParams.get("error"));
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => login(loginId.trim(), password),
    onSuccess: (me) => {
      replaceSession(queryClient, me);
      router.replace(next);
    },
    onError: () => setPassword(""),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!loginId.trim() || !password) return;
    mutation.mutate();
  }

  const error = mutation.isError
    ? mutation.error instanceof Error ? mutation.error.message : "로그인에 실패했습니다."
    : mutation.isIdle ? redirectError : null;

  return (
    <form className={styles.form} onSubmit={onSubmit} aria-label="로그인">
      <h1>로그인</h1>
      <p className={styles.lead}>메타볼레 계정으로 들어오세요.</p>
      <label className={styles.field}>
        아이디 또는 이메일
        <input
          className={styles.input}
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          value={loginId}
          onChange={(e) => setLoginId(e.target.value)}
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
      {error && <p className={styles.error} role="alert">{error}</p>}
      <button type="submit" className={styles.primary} disabled={mutation.isPending}>
        {mutation.isPending ? "확인 중…" : "로그인"}
      </button>
      <GoogleButton next={next} />
      <p className={styles.switch}>
        계정이 없으신가요?
        <Link href={signupHref(next)} prefetch={false}>회원가입</Link>
      </p>
    </form>
  );
}
