"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import type { AccessRule, AccessRuleCreate, IpBlock, IpBlockCreate, RuleTarget } from "@/shared/api/types";
import { createAccessRule, createIpBlock, deleteAccessRule, deleteIpBlock, fetchCurrentDevice } from "../api";
import { useAdminQuery } from "../hooks/use-admin-query";
import { BLOCK_TTL_OPTIONS, deviceLabel, formatDateTime } from "../lib/format";
import { Badge, Empty, Notice, Section } from "./admin-ui";
import styles from "./admin.module.css";

export const QUICK_BLOCK_MINUTES = 1_440;

export function useSecurityMutations() {
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "security"] });
  const block = useMutation({ mutationFn: (body: IpBlockCreate) => createIpBlock(body), onSuccess: refresh });
  const unblock = useMutation({ mutationFn: (ip: string) => deleteIpBlock(ip), onSuccess: refresh });
  const addRule = useMutation({ mutationFn: (body: AccessRuleCreate) => createAccessRule(body), onSuccess: refresh });
  const removeRule = useMutation({ mutationFn: (id: number) => deleteAccessRule(id), onSuccess: refresh });
  return { block, unblock, addRule, removeRule };
}

type SecurityMutations = ReturnType<typeof useSecurityMutations>;

interface TargetOption {
  value: RuleTarget;
  label: string;
  field: string;
  placeholder: string;
}

interface ListEntry {
  target: RuleTarget;
  value: string;
  note: string;
  ttl: number | null;
}

const IP_OPTION = (field: string, placeholder: string): TargetOption => ({ value: "ip", label: "IP", field, placeholder });
const DEVICE_OPTION: TargetOption = { value: "device", label: "디바이스", field: "디바이스 ID", placeholder: "이벤트 탭의 22자 ID" };
const BLACKLIST_TARGETS = [IP_OPTION("IP 주소", "203.0.113.10"), DEVICE_OPTION];
const WHITELIST_TARGETS = [{ ...IP_OPTION("IP 또는 대역", "10.0.0.0/8"), label: "IP·대역" }, DEVICE_OPTION];

function ListForm({ label, targets, noteLabel, notePlaceholder, submitLabel, defaultTtl, onSubmit, isPending, error, myDevice }: {
  label: string;
  targets: TargetOption[];
  noteLabel: string;
  notePlaceholder: string;
  submitLabel: string;
  defaultTtl: number | null;
  onSubmit: (entry: ListEntry) => void;
  isPending: boolean;
  error: unknown;
  myDevice?: string | null;
}) {
  const [target, setTarget] = useState<RuleTarget>(targets[0].value);
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [ttl, setTtl] = useState<number | null>(defaultTtl);
  const option = targets.find((t) => t.value === target) ?? targets[0];

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!value.trim()) return;
    onSubmit({ target, value: value.trim(), note: note.trim(), ttl });
    setValue("");
    setNote("");
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-label={label}>
      <label className={styles.field}>
        대상
        <select className={styles.select} value={target} onChange={(e) => { setTarget(e.target.value as RuleTarget); setValue(""); }}>
          {targets.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </label>
      <label className={styles.field}>
        {option.field}
        <input className={styles.input} value={value} onChange={(e) => setValue(e.target.value)} placeholder={option.placeholder} required />
      </label>
      <label className={`${styles.field} ${styles.fieldGrow}`}>
        {noteLabel}
        <input className={styles.input} value={note} onChange={(e) => setNote(e.target.value)} placeholder={notePlaceholder} />
      </label>
      <label className={styles.field}>
        기간
        <select
          className={styles.select}
          value={ttl ?? "forever"}
          onChange={(e) => setTtl(e.target.value === "forever" ? null : Number(e.target.value))}
        >
          {BLOCK_TTL_OPTIONS.map((o) => <option key={o.label} value={o.minutes ?? "forever"}>{o.label}</option>)}
        </select>
      </label>
      <button type="submit" className={styles.primaryButton} disabled={isPending}>{submitLabel}</button>
      {myDevice && (
        <button type="button" className={styles.ghostButton} onClick={() => { setTarget("device"); setValue(myDevice); }}>
          내 디바이스 넣기
        </button>
      )}
      {error instanceof Error && <p className={`${styles.formError} ${styles.fullRow}`} role="alert">{error.message}</p>}
    </form>
  );
}

function Expiry({ at }: { at: string | null }) {
  return at ? <>{formatDateTime(at)}</> : <Badge tone="warn">무기한</Badge>;
}

function RulesTable({ rules, canOperate, onRemove, pendingId, removeLabel, showTarget }: {
  rules: AccessRule[];
  canOperate: boolean;
  onRemove: (id: number) => void;
  pendingId: number | null;
  removeLabel: string;
  showTarget: boolean;
}) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {showTarget && <th>대상</th>}<th>값</th><th>메모</th><th>등록 시각</th><th>만료</th><th>처리자</th>
            {canOperate && <th>조치</th>}
          </tr>
        </thead>
        <tbody>
          {rules.map((rule) => (
            <tr key={rule.id}>
              {showTarget && <td><Badge>{rule.target === "ip" ? "IP·대역" : "디바이스"}</Badge></td>}
              <td className={styles.mono}>{rule.value}</td>
              <td>{rule.note || <span className={styles.muted}>—</span>}</td>
              <td className={styles.muted}>{formatDateTime(rule.created_at)}</td>
              <td><Expiry at={rule.expires_at} /></td>
              <td className={styles.muted}>{rule.created_by ?? "—"}</td>
              {canOperate && (
                <td>
                  <button type="button" className={styles.dangerButton} onClick={() => onRemove(rule.id)} disabled={pendingId === rule.id}>
                    {removeLabel}
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BlacklistPanel({ blocks, rules, canOperate, mutations }: {
  blocks: IpBlock[] | undefined;
  rules: AccessRule[];
  canOperate: boolean;
  mutations: SecurityMutations;
}) {
  const { block, unblock, addRule, removeRule } = mutations;
  const devices = rules.filter((r) => r.policy === "deny");
  const submit = ({ target, value, note, ttl }: ListEntry) =>
    target === "ip"
      ? block.mutate({ ip: value, reason: note, ttl_minutes: ttl })
      : addRule.mutate({ policy: "deny", target, value, note, ttl_minutes: ttl });

  return (
    <>
      {canOperate ? (
        <Section title="차단 추가">
          <ListForm
            label="블랙리스트 추가" targets={BLACKLIST_TARGETS} noteLabel="사유" notePlaceholder="수동 차단"
            submitLabel="차단 추가" defaultTtl={QUICK_BLOCK_MINUTES} onSubmit={submit}
            isPending={block.isPending || addRule.isPending} error={block.error ?? addRule.error}
          />
        </Section>
      ) : (
        <Notice>일반 회원은 차단 목록을 볼 수만 있습니다. 차단·해제는 관리자 권한이 필요합니다.</Notice>
      )}
      <Section title="차단 중인 IP" aside={<p>차단 IP는 /admin 경로 접근이 거부됩니다</p>} flush>
        {!blocks?.length ? (
          <Empty>차단 중인 IP가 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr><th>IP</th><th>사유</th><th>차단 시각</th><th>만료</th><th>처리자</th>{canOperate && <th>조치</th>}</tr>
              </thead>
              <tbody>
                {blocks.map((b) => (
                  <tr key={b.ip}>
                    <td className={styles.mono}>{b.ip}</td>
                    <td>{b.reason}</td>
                    <td className={styles.muted}>{formatDateTime(b.created_at)}</td>
                    <td><Expiry at={b.expires_at} /></td>
                    <td className={styles.muted}>{b.created_by ?? "—"}</td>
                    {canOperate && (
                      <td>
                        <button
                          type="button"
                          className={styles.dangerButton}
                          onClick={() => unblock.mutate(b.ip)}
                          disabled={unblock.isPending && unblock.variables === b.ip}
                        >
                          해제
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
      <Section title="차단 중인 디바이스" aside={<p>IP가 바뀌어도 같은 브라우저면 막힙니다 · 쿠키를 지우면 새 디바이스가 됩니다</p>} flush>
        {!devices.length ? (
          <Empty>차단 중인 디바이스가 없습니다.</Empty>
        ) : (
          <RulesTable
            rules={devices} canOperate={canOperate} onRemove={(id) => removeRule.mutate(id)}
            pendingId={removeRule.isPending ? removeRule.variables ?? null : null} removeLabel="해제" showTarget={false}
          />
        )}
      </Section>
    </>
  );
}

export function WhitelistPanel({ rules, canOperate, mutations }: {
  rules: AccessRule[];
  canOperate: boolean;
  mutations: SecurityMutations;
}) {
  const { addRule, removeRule } = mutations;
  const device = useAdminQuery(["admin", "security", "current-device"], fetchCurrentDevice);
  const allowed = rules.filter((r) => r.policy === "allow");
  const me = device.data;

  return (
    <>
      <Notice>
        화이트리스트에 있는 IP·대역·디바이스는 자동 차단과 로그인 실패 횟수 제한에 걸리지 않습니다. 같은 IP가 자동 차단돼도
        화이트리스트 디바이스는 들어올 수 있습니다. 관리자가 직접 막은 IP·디바이스는 화이트리스트여도 막힙니다.
      </Notice>
      {me?.device_id && (
        <p className={styles.ruleNote}>
          지금 디바이스: {deviceLabel(me.user_agent)} · <span className={styles.mono}>{me.device_id}</span>
          {me.allowed ? " · 화이트리스트에 있음" : ""}
        </p>
      )}
      {canOperate && (
        <Section title="화이트리스트 추가">
          <ListForm
            label="화이트리스트 추가" targets={WHITELIST_TARGETS} noteLabel="메모" notePlaceholder="사무실·내 노트북"
            submitLabel="추가" defaultTtl={null} onSubmit={({ target, value, note, ttl }) =>
              addRule.mutate({ policy: "allow", target, value, note, ttl_minutes: ttl })}
            isPending={addRule.isPending} error={addRule.error} myDevice={me?.device_id}
          />
        </Section>
      )}
      <Section title="화이트리스트" aside={<p>대역은 CIDR(예: 10.0.0.0/8) · IPv4는 /8보다 좁게</p>} flush>
        {!allowed.length ? (
          <Empty>화이트리스트가 비어 있습니다.</Empty>
        ) : (
          <RulesTable
            rules={allowed} canOperate={canOperate} onRemove={(id) => removeRule.mutate(id)}
            pendingId={removeRule.isPending ? removeRule.variables ?? null : null} removeLabel="삭제" showTarget
          />
        )}
      </Section>
    </>
  );
}
