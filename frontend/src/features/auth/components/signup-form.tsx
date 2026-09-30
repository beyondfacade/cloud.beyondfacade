"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { loginHref, replaceSession, safeNext } from "@/shared/auth/session";
import { signup } from "../api";
import { GoogleButton } from "./google-button";
import styles from "./auth.module.css";

export function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const next = safeNext(searchParams.get("next"));
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mismatch, setMismatch] = useState(false);

  const mutation = useMutation({
    mutationFn: () => signup({ username: username.trim(), email: email.trim(), password }),
    onSuccess: (me) => {
      replaceSession(queryClient, me);
      router.replace(next);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!username.trim() || !email.trim() || !password) return;
    setMismatch(password !== confirm);
    if (password !== confirm) return;
    mutation.mutate();
  }

  const error = mismatch
    ? "비밀번호가 서로 다릅니다."
    : mutation.isError ? mutation.error instanceof Error ? mutation.error.message : "가입하지 못했습니다." : null;

  return (
    <form className={styles.form} onSubmit={onSubmit} aria-label="회원가입">
      <h1>회원가입</h1>
      <p className={styles.lead}>가입하면 일반 등급으로 바로 이용할 수 있습니다.</p>
      <div className={styles.field}>
        <label htmlFor="signup-username">아이디</label>
        <input
          id="signup-username"
          className={styles.input}
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          value={username}
          onChange={(e) => setUsername(e.target.value.toLowerCase())}
          aria-describedby="signup-username-hint"
          required
        />
        <span id="signup-username-hint" className={styles.hint}>영문 소문자·숫자로 시작하는 3~32자 (. _ - 사용 가능)</span>
      </div>
      <label className={styles.field}>
        이메일
        <input
          className={styles.input}
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </label>
      <div className={styles.field}>
        <label htmlFor="signup-password">비밀번호</label>
        <input
          id="signup-password"
          className={styles.input}
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-describedby="signup-password-hint"
          required
        />
        <span id="signup-password-hint" className={styles.hint}>12자 이상</span>
      </div>
      <label className={styles.field}>
        비밀번호 확인
        <input
          className={styles.input}
          name="password-confirm"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
        />
      </label>
      {error && <p className={styles.error} role="alert">{error}</p>}
      <button type="submit" className={styles.primary} disabled={mutation.isPending}>
        {mutation.isPending ? "가입 중…" : "가입하기"}
      </button>
      <GoogleButton next={next} />
      <p className={styles.switch}>
        이미 계정이 있으신가요?
        <Link href={loginHref(next)} prefetch={false}>로그인</Link>
      </p>
    </form>
  );
}
