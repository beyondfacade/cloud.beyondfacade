"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useDeferredValue, useEffect, useRef, useState, type FormEvent } from "react";
import type { AdminMe, AdminRole, AdminUser, AdminUserFilter, AdminUserStatus } from "@/shared/api/types";
import {
  changeAdminRole,
  changeMyPassword,
  createAdminUser,
  fetchAdminSessions,
  fetchAdminUsers,
  resetAdminPassword,
  revokeAdminSessions,
  setAdminActive,
} from "../api";
import { useAdminMe, useAdminQuery } from "../hooks/use-admin-query";
import { formatCount, formatDateTime, formatRelative, ROLE } from "../lib/format";
import { ROOM_BY_KEY } from "../lib/rooms";
import { Badge, Empty, errorMessage, Notice, RoomError, Section, Segment, StatStrip, Tabs, type StatItem } from "./admin-ui";
import { RoomHeader } from "./room-header";
import styles from "./admin.module.css";

const ROOM = ROOM_BY_KEY.users;
const USERS_KEY = ["admin", "users"] as const;
const EVERYONE: AdminUserFilter = { q: "", role: null, status: "all" };
/** 백엔드 account_policy와 같은 하한 — 서버가 최종 판정한다. */
const MIN_PASSWORD = 12;

const STATUS_OPTIONS: { value: AdminUserStatus; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "active", label: "활성" },
  { value: "suspended", label: "정지" },
];
const ROLE_OPTIONS = Object.entries(ROLE).map(([value, r]) => ({ value: value as AdminRole, label: r.label }));

function summaryItems(everyone: AdminUser[], shown: number): StatItem[] {
  const suspended = everyone.filter((u) => !u.is_active).length;
  const operators = everyone.filter((u) => u.is_active && u.role === "operator").length;
  return [
    { label: "조회 유저", value: `${formatCount(shown)}명` },
    { label: "전체 계정", value: formatCount(everyone.length) },
    { label: "접속 정지", value: `${formatCount(suspended)}명`, tone: suspended ? "warn" : "ok" },
    {
      label: "활성 관리자", value: formatCount(operators), tone: operators <= 1 ? "warn" : undefined,
      hint: operators <= 1 ? "마지막 관리자는 강등·정지할 수 없습니다" : undefined,
    },
    { label: "활성 세션", value: formatCount(everyone.reduce((sum, u) => sum + u.active_sessions, 0)) },
  ];
}

function useInvalidateUsers() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: USERS_KEY });
}

function loginMethods(user: AdminUser): string {
  return [user.has_password && "비밀번호", user.has_google && "구글"].filter(Boolean).join(" · ") || "—";
}

function passwordProblem(password: string): string | null {
  return password.length < MIN_PASSWORD ? `비밀번호는 ${MIN_PASSWORD}자 이상이어야 합니다.` : null;
}

function CreateUserForm({ onCreated }: { onCreated: (username: string) => void }) {
  const invalidate = useInvalidateUsers();
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<AdminRole>("viewer");
  const [password, setPassword] = useState("");
  const create = useMutation({
    mutationFn: () => createAdminUser({ username: username.trim(), role, password }),
    onSuccess: (user) => {
      void invalidate();
      onCreated(user.username);
    },
  });
  const problem = password ? passwordProblem(password) : null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (username.trim() && !passwordProblem(password)) create.mutate();
  }

  return (
    <Section title="계정 추가" aside={<p>아이디는 영문 소문자·숫자·._- 3~32자</p>}>
      <form className={styles.form} onSubmit={submit} aria-label="계정 추가">
        <label className={styles.field}>
          아이디
          <input className={styles.input} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" maxLength={32} />
        </label>
        <label className={styles.field}>
          등급
          <select className={styles.select} value={role} onChange={(e) => setRole(e.target.value as AdminRole)}>
            {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        <label className={`${styles.field} ${styles.fieldGrow}`}>
          초기 비밀번호
          <input className={styles.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        </label>
        <button type="submit" className={styles.primaryButton} disabled={create.isPending || !username.trim() || !!passwordProblem(password)}>
          {create.isPending ? "만드는 중…" : "계정 만들기"}
        </button>
      </form>
      {problem && <p className={styles.formError}>{problem}</p>}
      {create.isError && <p className={styles.formError} role="alert">{errorMessage(create.error, "계정을 만들지 못했습니다")}</p>}
    </Section>
  );
}

function RoleBlock({ user }: { user: AdminUser }) {
  const invalidate = useInvalidateUsers();
  const change = useMutation({ mutationFn: (role: AdminRole) => changeAdminRole(user.username, role), onSuccess: () => void invalidate() });
  return (
    <div className={styles.panelBlock}>
      <h3>등급</h3>
      <Segment label="등급 변경" options={ROLE_OPTIONS} value={user.role} onChange={(role) => role !== user.role && change.mutate(role)} />
      {change.isError && <p className={styles.formError} role="alert">{errorMessage(change.error, "등급을 바꾸지 못했습니다")}</p>}
    </div>
  );
}

function StatusBlock({ user }: { user: AdminUser }) {
  const invalidate = useInvalidateUsers();
  const [confirming, setConfirming] = useState(false);
  const change = useMutation({
    mutationFn: (active: boolean) => setAdminActive(user.username, active),
    onSuccess: () => { setConfirming(false); void invalidate(); },
  });
  return (
    <div className={styles.panelBlock}>
      <h3>접속 상태</h3>
      {user.is_active ? (
        confirming ? (
          <div className={styles.stack}>
            <p className={styles.muted}>정지하면 이 계정의 세션이 모두 끊기고 로그인할 수 없습니다.</p>
            <div className={styles.form}>
              <button type="button" className={styles.dangerButton} onClick={() => change.mutate(false)} disabled={change.isPending}>정지 확인</button>
              <button type="button" className={styles.ghostButton} onClick={() => setConfirming(false)}>취소</button>
            </div>
          </div>
        ) : (
          <button type="button" className={styles.dangerButton} onClick={() => setConfirming(true)}>접속 정지</button>
        )
      ) : (
        <button type="button" className={styles.primaryButton} onClick={() => change.mutate(true)} disabled={change.isPending}>정지 해제</button>
      )}
      {change.isError && <p className={styles.formError} role="alert">{errorMessage(change.error, "상태를 바꾸지 못했습니다")}</p>}
    </div>
  );
}

function ResetPasswordBlock({ user }: { user: AdminUser }) {
  const invalidate = useInvalidateUsers();
  const [password, setPassword] = useState("");
  const reset = useMutation({
    mutationFn: () => resetAdminPassword(user.username, password),
    onSuccess: () => { setPassword(""); void invalidate(); },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!passwordProblem(password)) reset.mutate();
  }

  return (
    <form className={styles.panelBlock} onSubmit={submit} aria-label="비밀번호 재설정">
      <h3>비밀번호 재설정</h3>
      <div className={styles.form}>
        <label className={`${styles.field} ${styles.fieldGrow}`}>
          <span className="sr-only">새 비밀번호</span>
          <input
            className={styles.input} type="password" value={password} placeholder={`${MIN_PASSWORD}자 이상`}
            onChange={(e) => { setPassword(e.target.value); reset.reset(); }} autoComplete="new-password" aria-label="새 비밀번호"
          />
        </label>
        <button type="submit" className={styles.ghostButton} disabled={reset.isPending || !!passwordProblem(password)}>재설정</button>
      </div>
      {reset.isSuccess && <p className={styles.formOk} role="status">재설정했습니다 — 기존 세션은 모두 끊겼습니다.</p>}
      {reset.isError && <p className={styles.formError} role="alert">{errorMessage(reset.error, "재설정하지 못했습니다")}</p>}
    </form>
  );
}

function SessionsBlock({ user, isSelf }: { user: AdminUser; isSelf: boolean }) {
  const invalidate = useInvalidateUsers();
  const sessions = useAdminQuery([...USERS_KEY, user.username, "sessions"], () => fetchAdminSessions(user.username));
  const revoke = useMutation({ mutationFn: () => revokeAdminSessions(user.username), onSuccess: () => void invalidate() });
  const items = sessions.data?.items ?? [];
  const revocable = items.filter((s) => !s.current).length;

  return (
    <div className={styles.panelBlock}>
      <h3>활성 세션</h3>
      {sessions.isError ? (
        <p className={styles.formError}>{errorMessage(sessions.error, "세션을 불러오지 못했습니다")}</p>
      ) : !items.length ? (
        <p className={styles.muted}>{sessions.isPending ? "불러오는 중…" : "활성 세션이 없습니다."}</p>
      ) : (
        <ul className={styles.sessions} aria-label="세션 목록">
          {items.map((s) => (
            <li key={s.id}>
              <span className={styles.mono}>{s.ip ?? "IP 없음"}</span>
              {s.current && <Badge tone="ok">현재 세션</Badge>}
              <span className={styles.muted}>{formatDateTime(s.created_at)} 시작 · {formatDateTime(s.expires_at)} 만료</span>
            </li>
          ))}
        </ul>
      )}
      <div className={styles.form}>
        <button
          type="button" className={styles.dangerButton}
          onClick={() => revoke.mutate()} disabled={revoke.isPending || !revocable}
        >
          {isSelf ? "다른 세션 모두 끊기" : "세션 모두 끊기"}
        </button>
      </div>
      {revoke.isSuccess && <p className={styles.formOk} role="status">{revoke.data.revoked}개 세션을 끊었습니다.</p>}
      {revoke.isError && <p className={styles.formError} role="alert">{errorMessage(revoke.error, "세션을 끊지 못했습니다")}</p>}
    </div>
  );
}

function MyPasswordBlock() {
  const invalidate = useInvalidateUsers();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const change = useMutation({
    mutationFn: () => changeMyPassword(current, next),
    onSuccess: () => { setCurrent(""); setNext(""); setConfirm(""); void invalidate(); },
  });
  const problem = next ? passwordProblem(next) ?? (confirm && confirm !== next ? "새 비밀번호가 서로 다릅니다." : null) : null;
  const ready = current && next && confirm === next && !passwordProblem(next);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (ready) change.mutate();
  }

  return (
    <form className={`${styles.panelBlock} ${styles.stack}`} onSubmit={submit} aria-label="내 비밀번호 변경">
      <h3>내 비밀번호 변경</h3>
      <label className={styles.field}>
        현재 비밀번호
        <input className={styles.input} type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
      </label>
      <label className={styles.field}>
        새 비밀번호
        <input className={styles.input} type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
      </label>
      <label className={styles.field}>
        새 비밀번호 확인
        <input className={styles.input} type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
      </label>
      {problem && <p className={styles.formError}>{problem}</p>}
      <div className={styles.form}>
        <button type="submit" className={styles.primaryButton} disabled={change.isPending || !ready}>
          {change.isPending ? "바꾸는 중…" : "비밀번호 변경"}
        </button>
      </div>
      {change.isSuccess && <p className={styles.formOk} role="status">변경했습니다 — 이 세션을 뺀 나머지 세션은 끊겼습니다.</p>}
      {change.isError && <p className={styles.formError} role="alert">{errorMessage(change.error, "변경하지 못했습니다")}</p>}
    </form>
  );
}

function UserPanel({ user, me, now, onClose }: { user: AdminUser; me: AdminMe; now: number; onClose: () => void }) {
  const isSelf = user.username === me.username;
  const ref = useRef<HTMLDivElement>(null);
  // 좁은 화면에서는 패널이 표 아래로 내려간다 — 열 때 보이는 곳으로 끌어온다.
  useEffect(() => {
    ref.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, []);
  return (
    <div className={styles.panel} ref={ref}>
      <Section
        title={`계정 ${user.username}`}
        aside={<button type="button" className={styles.ghostButton} onClick={onClose}>닫기</button>}
      >
        <dl className={styles.kv}>
          <dt>등급</dt><dd><Badge tone={ROLE[user.role].tone}>{ROLE[user.role].label}</Badge></dd>
          <dt>이메일</dt><dd>{user.email ?? "—"}</dd>
          <dt>가입 방식</dt><dd>{loginMethods(user)}</dd>
          <dt>상태</dt><dd><Badge tone={user.is_active ? "ok" : "danger"} dot>{user.is_active ? "활성" : "정지"}</Badge></dd>
          <dt>마지막 로그인</dt><dd>{formatRelative(user.last_login_at, now)}</dd>
          <dt>생성</dt><dd>{formatDateTime(user.created_at)}</dd>
        </dl>
        {isSelf ? (
          <>
            <div className={styles.panelBlock}><Notice>본인 계정의 등급·상태는 바꿀 수 없습니다. 다른 관리자에게 요청하세요.</Notice></div>
            {user.has_password ? <MyPasswordBlock /> : (
              <div className={styles.panelBlock}><Notice>구글로 가입한 계정이라 비밀번호가 없습니다. 구글 로그인으로 들어오세요.</Notice></div>
            )}
            <SessionsBlock user={user} isSelf />
          </>
        ) : me.can_operate ? (
          <>
            <RoleBlock user={user} />
            <StatusBlock user={user} />
            <ResetPasswordBlock user={user} />
            <SessionsBlock user={user} isSelf={false} />
          </>
        ) : (
          <div className={styles.panelBlock}><Notice>계정 변경과 세션 관리는 관리자 권한이 필요합니다.</Notice></div>
        )}
      </Section>
    </div>
  );
}

function UserTable({ users, me, selected, now, onSelect }: {
  users: AdminUser[];
  me: string | undefined;
  selected: string | null;
  now: number;
  onSelect: (username: string) => void;
}) {
  if (!users.length) return <Empty>조건에 맞는 계정이 없습니다.</Empty>;
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead><tr><th>계정</th><th>이메일</th><th>가입 방식</th><th>등급</th><th>상태</th><th className={styles.num}>세션</th><th>마지막 로그인</th><th>생성</th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.username} className={u.username === selected ? styles.rowSelected : undefined}>
              <td>
                <button
                  type="button" className={styles.linkButton} onClick={() => onSelect(u.username)}
                  aria-current={u.username === selected ? "true" : undefined}
                >
                  {u.username}
                </button>
                {u.username === me && <> <Badge>나</Badge></>}
              </td>
              <td className={styles.muted}>{u.email ?? "—"}</td>
              <td className={styles.muted}>{loginMethods(u)}</td>
              <td><Badge tone={ROLE[u.role].tone}>{ROLE[u.role].label}</Badge></td>
              <td><Badge tone={u.is_active ? "ok" : "danger"} dot>{u.is_active ? "활성" : "정지"}</Badge></td>
              <td className={styles.num}>{formatCount(u.active_sessions)}</td>
              <td>{formatRelative(u.last_login_at, now)}</td>
              <td className={styles.muted}>{formatDateTime(u.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UserListPanel({ me, everyone, now }: { me: AdminMe | undefined; everyone: AdminUser[]; now: number }) {
  const param = useSearchParams().get("user");
  const [selected, setSelected] = useState<string | null>(param);
  const [seenParam, setSeenParam] = useState(param);
  if (param !== seenParam) {
    setSeenParam(param);
    setSelected(param);
  }
  const [filter, setFilter] = useState<AdminUserFilter>(EVERYONE);
  const [creating, setCreating] = useState(false);
  const q = useDeferredValue(filter.q);
  const applied = { ...filter, q };
  const list = useAdminQuery([...USERS_KEY, applied], () => fetchAdminUsers(applied), ROOM.pollMs, { keepPrevious: true });
  const users = list.data?.items ?? [];
  const current = everyone.find((u) => u.username === selected) ?? null;

  return (
    <>
      <StatStrip label="계정 요약" items={summaryItems(everyone, users.length)} />
      <div className={styles.afterStats}>
        <div className={styles.toolbar}>
          <div className={styles.form} role="search">
            <label className={`${styles.field} ${styles.fieldGrow}`}>
              검색
              <input
                className={styles.input} type="search" value={filter.q} placeholder="아이디·이메일 일부"
                onChange={(e) => setFilter({ ...filter, q: e.target.value })}
              />
            </label>
            <label className={styles.field}>
              등급
              <select
                className={styles.select} value={filter.role ?? ""}
                onChange={(e) => setFilter({ ...filter, role: (e.target.value || null) as AdminRole | null })}
              >
                <option value="">전체</option>
                {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <Segment label="접속 상태" options={STATUS_OPTIONS} value={filter.status} onChange={(status) => setFilter({ ...filter, status })} />
          </div>
          {me?.can_operate && (
            <button type="button" className={styles.primaryButton} onClick={() => setCreating((v) => !v)} aria-expanded={creating}>
              {creating ? "추가 닫기" : "계정 추가"}
            </button>
          )}
        </div>
        {creating && (
          <div className={styles.toolbar}>
            <CreateUserForm onCreated={(username) => { setCreating(false); setSelected(username); }} />
          </div>
        )}
        <div className={current ? styles.people : undefined}>
          <Section title="유저 목록" aside={<p>{list.isFetching ? "갱신 중…" : `${formatCount(users.length)}명`}</p>} flush>
            {list.isError ? <RoomError error={list.error} /> : (
              <UserTable users={users} me={me?.username} selected={selected} now={now} onSelect={setSelected} />
            )}
          </Section>
          {current && me && <UserPanel key={current.username} user={current} me={me} now={now} onClose={() => setSelected(null)} />}
        </div>
      </div>
    </>
  );
}

export function UsersRoom() {
  const me = useAdminMe();
  const everyone = useAdminQuery([...USERS_KEY, EVERYONE], () => fetchAdminUsers(EVERYONE), ROOM.pollMs);
  const data = everyone.data;

  return (
    <>
      <RoomHeader
        room={ROOM}
        updatedAt={everyone.dataUpdatedAt}
        isFetching={everyone.isFetching}
        isError={everyone.isError}
        onRefresh={() => void everyone.refetch()}
      />
      {everyone.isError && !data && <RoomError error={everyone.error} />}
      {data && (
        <Tabs
          label="인사팀 탭"
          tabs={[{ key: "users", label: "유저 목록", count: data.items.length, render: () => <UserListPanel me={me.data} everyone={data.items} now={everyone.dataUpdatedAt} /> }]}
        />
      )}
    </>
  );
}
