"use client";

import { useRef, useState, type ChangeEvent } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { AdminMe } from "@/shared/api/types";
import { avatarUrl, GRADE_LABEL, loginHref, SESSION_QUERY_KEY } from "@/shared/auth/session";
import { useSession } from "@/shared/auth/use-session";
import { INDUSTRY_GROUPS, INDUSTRY_LABELS } from "@/shared/industries";
import { AVATAR_TYPES, changeSpecialty, MAX_AVATAR_BYTES, uploadAvatar } from "../api";

const CARD = "flex flex-col gap-4 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-5";
const BUTTON = "w-fit rounded-md border border-[var(--border)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] hover:border-[var(--accent)] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";
const LABELS: readonly string[] = Object.values(INDUSTRY_LABELS);

/** /mypage — 헤더의 내 계정명·등급을 누르면 온다. 프로필 사진은 누구나, 전문 업종은 전문가만 고친다. */
export function MyPage() {
  const session = useSession();
  const me = session.data;

  if (session.isPending) return <main aria-label="마이페이지" className="mx-auto max-w-2xl px-4 py-10" aria-busy="true" />;
  if (!me) {
    return (
      <main aria-label="마이페이지" className="mx-auto flex max-w-2xl flex-col gap-3 px-4 py-10">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">마이페이지</h1>
        <p className="text-sm text-[var(--text-secondary)]">로그인하면 프로필을 관리할 수 있어요.</p>
        <Link href={loginHref("/mypage")} className={BUTTON}>로그인</Link>
      </main>
    );
  }

  return (
    <main aria-label="마이페이지" className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">마이페이지</h1>
        <p className="text-sm text-[var(--text-secondary)]">
          {me.username} · {GRADE_LABEL[me.role]}
        </p>
      </header>
      <AvatarCard me={me} />
      {me.role === "expert" && <SpecialtyCard me={me} />}
    </main>
  );
}

function useSaveMe() {
  const queryClient = useQueryClient();
  return (me: AdminMe) => {
    queryClient.setQueryData(SESSION_QUERY_KEY, me);
    void queryClient.invalidateQueries({ queryKey: ["chat"] });
  };
}

function AvatarCard({ me }: { me: AdminMe }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const upload = useMutation({ mutationFn: uploadAvatar, onSuccess: useSaveMe() });

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    upload.reset();
    if (!AVATAR_TYPES.includes(file.type)) return setProblem("PNG·JPG·WebP 사진만 올릴 수 있어요.");
    if (file.size > MAX_AVATAR_BYTES) return setProblem("사진은 1MB 이하만 올릴 수 있어요.");
    setProblem(null);
    upload.mutate(file);
  };
  const error = problem ?? (upload.isError ? upload.error.message : null);

  return (
    <section aria-labelledby="mypage-avatar" className={CARD}>
      <h2 id="mypage-avatar" className="text-base font-semibold text-[var(--text-primary)]">프로필 사진</h2>
      <div className="flex items-center gap-5">
        <span className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-full border border-[var(--border)] text-[var(--text-secondary)]">
          {me.avatar_version ? (
            <img src={avatarUrl(me.id, me.avatar_version)} alt="내 프로필 사진" width={80} height={80} className="size-full object-cover" />
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor" className="size-12" aria-label="기본 프로필">
              <circle cx="12" cy="8.5" r="4" />
              <path d="M4.5 20.5a7.5 7.5 0 0 1 15 0z" />
            </svg>
          )}
        </span>
        <div className="flex flex-col gap-2">
          <p className="text-sm text-[var(--text-secondary)]">PNG·JPG·WebP, 1MB 이하. 채팅 대화 목록·전문가 목록에 보여요.</p>
          <button type="button" className={BUTTON} onClick={() => fileRef.current?.click()} disabled={upload.isPending}>
            {upload.isPending ? "올리는 중…" : "사진 선택"}
          </button>
          <input ref={fileRef} type="file" accept={AVATAR_TYPES.join(",")} hidden onChange={onFile} aria-label="프로필 사진 파일" />
        </div>
      </div>
      {error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
    </section>
  );
}

function SpecialtyCard({ me }: { me: AdminMe }) {
  const [draft, setDraft] = useState(me.specialty ?? "");
  const save = useMutation({ mutationFn: changeSpecialty, onSuccess: useSaveMe() });
  const unlisted = me.specialty && !LABELS.includes(me.specialty) ? me.specialty : null;

  return (
    <section aria-labelledby="mypage-specialty" className={CARD}>
      <h2 id="mypage-specialty" className="text-base font-semibold text-[var(--text-primary)]">전문 업종</h2>
      <p className="text-sm text-[var(--text-secondary)]">채팅 전문가 목록에 표시되고, 같은 업종을 분석 중인 회원에게 먼저 보여요.</p>
      <form
        className="flex flex-wrap items-center gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate(draft || null);
        }}
      >
        <select
          aria-label="전문 업종"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="rounded-md border border-[var(--border)] bg-transparent px-3 py-1.5 text-sm text-[var(--text-primary)]"
        >
          <option value="">선택 안 함</option>
          {unlisted && <option value={unlisted}>{unlisted}</option>}
          {INDUSTRY_GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.ids.map((id) => (
                <option key={id} value={INDUSTRY_LABELS[id]}>{INDUSTRY_LABELS[id]}</option>
              ))}
            </optgroup>
          ))}
        </select>
        <button type="submit" className={BUTTON} disabled={save.isPending || draft === (me.specialty ?? "")}>
          {save.isPending ? "저장 중…" : "저장"}
        </button>
        {save.isSuccess && <span role="status" className="text-sm text-[var(--text-secondary)]">저장했어요.</span>}
      </form>
      {save.isError && <p role="alert" className="text-sm text-[var(--danger)]">{save.error.message}</p>}
    </section>
  );
}
