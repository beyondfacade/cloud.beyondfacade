"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import type { AccessEventKind, AuditAction, SecurityAlert, SecurityEventFilter, SecurityOverview } from "@/shared/api/types";
import {
  fetchAccessRules,
  fetchAuditPage,
  fetchAutoDefense,
  fetchIpBlocks,
  fetchSecurityEvents,
  fetchSecurityOverview,
  setAutoDefense,
} from "../api";
import { useAdminMe, useAdminPages, useAdminQuery } from "../hooks/use-admin-query";
import {
  AUDIT_ACTION,
  EVENT_KIND,
  EVENT_WINDOWS,
  SEVERITY,
  deviceLabel,
  formatCount,
  formatDateTime,
  formatMinutes,
} from "../lib/format";
import { ROOM_BY_KEY } from "../lib/rooms";
import { BlacklistPanel, QUICK_BLOCK_MINUTES, WhitelistPanel, useSecurityMutations } from "./access-list-panels";
import { Badge, Empty, LoadMore, RoomError, Section, Segment, StatStrip, Tabs, type StatItem } from "./admin-ui";
import { RoomHeader } from "./room-header";
import styles from "./admin.module.css";

const ROOM = ROOM_BY_KEY.security;

function summaryItems(summary: SecurityOverview["summary"]): StatItem[] {
  return [
    { label: "이벤트 24h", value: formatCount(summary.events_24h) },
    { label: "로그인 실패", value: formatCount(summary.failed_logins_24h), tone: summary.failed_logins_24h ? "warn" : undefined },
    { label: "스캐너 탐색", value: formatCount(summary.scanner_probes_24h), tone: summary.scanner_probes_24h ? "warn" : undefined },
    { label: "서버 오류", value: formatCount(summary.server_errors_24h), tone: summary.server_errors_24h ? "danger" : undefined },
    { label: "열린 알림", value: formatCount(summary.open_alerts), tone: summary.open_alerts ? "danger" : "ok" },
    { label: "차단 IP", value: formatCount(summary.blocked_ips) },
  ];
}

const AUTO_DEFENSE_KEY = ["admin", "security", "auto-defense"];
const SWITCH_OPTIONS = [{ value: "on", label: "ON" }, { value: "off", label: "OFF" }] as const;

function AutoDefensePanel({ canOperate }: { canOperate: boolean }) {
  const queryClient = useQueryClient();
  const setting = useAdminQuery(AUTO_DEFENSE_KEY, fetchAutoDefense, ROOM.pollMs);
  const toggle = useMutation({
    mutationFn: (enabled: boolean) => setAutoDefense(enabled),
    onSuccess: (next) => {
      queryClient.setQueryData(AUTO_DEFENSE_KEY, next);
      void queryClient.invalidateQueries({ queryKey: ["admin", "security"] });
    },
  });
  const data = setting.data;
  if (!data) return setting.isError ? <Section title="자동 방어"><RoomError error={setting.error} /></Section> : null;

  const changed = data.updated_by ? `${data.updated_by} · ${formatDateTime(data.updated_at)} 변경` : "기본값";
  return (
    <Section
      title="자동 방어"
      aside={
        <div className={styles.headControls}>
          <p>{changed}</p>
          {canOperate ? (
            <Segment
              label="자동 방어 켜기·끄기"
              options={[...SWITCH_OPTIONS]}
              value={data.enabled ? "on" : "off"}
              onChange={(value) => value !== (data.enabled ? "on" : "off") && toggle.mutate(value === "on")}
            />
          ) : (
            <Badge tone={data.enabled ? "ok" : "danger"} dot>{data.enabled ? "ON" : "OFF"}</Badge>
          )}
        </div>
      }
    >
      <ul className={styles.ruleList} aria-label="자동 차단 규칙">
        {data.rules.map((rule) => (
          <li key={rule.rule}>
            <strong>{rule.title}</strong>
            <span>
              같은 IP가 {formatMinutes(rule.window_minutes)} 안에 {formatCount(rule.threshold)}회 → {formatMinutes(rule.block_minutes)} 차단
              · 풀린 뒤 다시 걸리면 {formatMinutes(rule.repeat_block_minutes)}
            </span>
          </li>
        ))}
      </ul>
      <p className={styles.ruleNote}>
        {data.enabled
          ? "차단된 IP는 /admin 경로에 접근할 수 없습니다. 서버 자신(루프백)은 차단하지 않고, 이미 걸린 수동 차단은 덮어쓰지 않습니다."
          : "꺼져 있는 동안에는 새 차단을 만들지 않습니다. 로그인은 IP당 10분 10회 실패 제한(429)만 적용되고, 이미 걸린 차단은 만료될 때까지 유지됩니다."}
      </p>
      {toggle.error instanceof Error && <p className={styles.formError} role="alert">{toggle.error.message}</p>}
    </Section>
  );
}

function AlertsPanel({ alerts, canOperate, onBlock, pendingIp }: {
  alerts: SecurityAlert[];
  canOperate: boolean;
  onBlock: (alert: SecurityAlert) => void;
  pendingIp: string | null;
}) {
  if (!alerts.length) return <Section title="열린 알림"><Empty>최근 창에서 규칙에 걸린 이상 징후가 없습니다.</Empty></Section>;
  return (
    <Section title="열린 알림" aside={<p>심각도 순 · 규칙별 집계</p>} flush>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr><th>심각도</th><th>알림</th><th>IP</th><th className={styles.num}>횟수</th><th>마지막</th><th>조치</th></tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <tr key={`${alert.rule}-${alert.ip ?? "all"}`}>
                <td><Badge tone={SEVERITY[alert.severity].tone} dot>{SEVERITY[alert.severity].label}</Badge></td>
                <td>{alert.title}</td>
                <td className={styles.mono}>{alert.ip ?? "—"}</td>
                <td className={styles.num}>{formatCount(alert.count)}</td>
                <td className={styles.muted}>{formatDateTime(alert.last_seen)}</td>
                <td>
                  {alert.blocked ? (
                    <Badge>차단됨</Badge>
                  ) : alert.ip && canOperate ? (
                    <button
                      type="button"
                      className={styles.dangerButton}
                      onClick={() => onBlock(alert)}
                      disabled={pendingIp === alert.ip}
                    >
                      24시간 차단
                    </button>
                  ) : (
                    <span className={styles.muted}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

const EVENT_KINDS = Object.entries(EVENT_KIND) as [AccessEventKind, (typeof EVENT_KIND)[AccessEventKind]][];
const AUDIT_ACTIONS = Object.entries(AUDIT_ACTION) as [AuditAction, (typeof AUDIT_ACTION)[AuditAction]][];

function EventsPanel() {
  const [filter, setFilter] = useState<SecurityEventFilter>({ kind: null, ip: "", hours: 24 });
  const [ipDraft, setIpDraft] = useState("");
  const pages = useAdminPages(["admin", "security", "events", filter], (before) => fetchSecurityEvents(filter, before));
  const byIp = (ip: string) => { setIpDraft(ip); setFilter({ ...filter, ip }); };

  function submit(event: FormEvent) {
    event.preventDefault();
    setFilter({ ...filter, ip: ipDraft.trim() });
  }

  return (
    <>
      <form className={`${styles.form} ${styles.filters}`} onSubmit={submit} aria-label="이벤트 검색">
        <label className={styles.field}>
          종류
          <select
            className={styles.select} value={filter.kind ?? ""}
            onChange={(e) => setFilter({ ...filter, kind: (e.target.value || null) as AccessEventKind | null })}
          >
            <option value="">전체</option>
            {EVENT_KINDS.map(([kind, k]) => <option key={kind} value={kind}>{k.label}</option>)}
          </select>
        </label>
        <label className={styles.field}>
          IP
          <input className={styles.input} value={ipDraft} onChange={(e) => setIpDraft(e.target.value)} placeholder="정확히 일치" />
        </label>
        <button type="submit" className={styles.ghostButton}>검색</button>
        {filter.ip && <button type="button" className={styles.ghostButton} onClick={() => byIp("")}>IP 해제</button>}
        <Segment label="검색 기간" options={EVENT_WINDOWS.map((w) => ({ value: w.hours, label: w.label }))} value={filter.hours} onChange={(hours) => setFilter({ ...filter, hours })} />
      </form>
      <Section title="접근 이벤트" aside={<p>최신순 · 보존 90일</p>} flush>
        {pages.isError ? (
          <RoomError error={pages.error} />
        ) : !pages.items.length ? (
          <Empty>{pages.isPending ? "불러오는 중…" : "조건에 맞는 이벤트가 없습니다."}</Empty>
        ) : (
          <>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr><th>시각</th><th>종류</th><th>IP</th><th>디바이스</th><th>요청</th><th className={styles.num}>상태</th><th>계정</th></tr>
                </thead>
                <tbody>
                  {pages.items.map((event, index) => (
                    <tr key={event.id ?? `${event.occurred_at}-${index}`}>
                      <td className={styles.muted}>{formatDateTime(event.occurred_at)}</td>
                      <td><Badge tone={EVENT_KIND[event.kind].tone}>{EVENT_KIND[event.kind].label}</Badge></td>
                      <td className={styles.mono}>
                        {event.ip ? (
                          <button type="button" className={styles.linkButton} onClick={() => byIp(event.ip ?? "")} title="이 IP만 보기">{event.ip}</button>
                        ) : "—"}
                      </td>
                      <td title={event.user_agent ?? undefined}>
                        {deviceLabel(event.user_agent)}
                        {event.device_id && <span className={`${styles.mono} ${styles.deviceId}`}>{event.device_id}</span>}
                      </td>
                      <td className={styles.mono}>{event.method} {event.path}</td>
                      <td className={styles.num}>{event.status_code}</td>
                      <td>{event.username ?? <span className={styles.muted}>—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <LoadMore hasMore={pages.hasNextPage} loading={pages.isFetchingNextPage} onMore={() => void pages.fetchNextPage()} shown={pages.items.length} />
          </>
        )}
      </Section>
    </>
  );
}

function AuditPanel() {
  const [action, setAction] = useState<AuditAction | null>(null);
  const pages = useAdminPages(["admin", "security", "audit", action], (before) => fetchAuditPage(action, before));
  return (
    <>
      <div className={`${styles.form} ${styles.filters}`}>
        <label className={styles.field}>
          행위
          <select className={styles.select} value={action ?? ""} onChange={(e) => setAction((e.target.value || null) as AuditAction | null)}>
            <option value="">전체</option>
            {AUDIT_ACTIONS.map(([key, a]) => <option key={key} value={key}>{a.label}</option>)}
          </select>
        </label>
      </div>
      <Section title="관리자 감사 로그" aside={<p>누가 무엇을 바꿨는지 · 보존 365일</p>} flush>
        {pages.isError ? (
          <RoomError error={pages.error} />
        ) : !pages.items.length ? (
          <Empty>{pages.isPending ? "불러오는 중…" : "기록된 관리자 행위가 없습니다."}</Empty>
        ) : (
          <>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>시각</th><th>행위</th><th>처리자</th><th>대상</th><th>상세</th><th>IP</th></tr></thead>
                <tbody>
                  {pages.items.map((entry, index) => (
                    <tr key={entry.id ?? `${entry.occurred_at}-${index}`}>
                      <td className={styles.muted}>{formatDateTime(entry.occurred_at)}</td>
                      <td><Badge tone={AUDIT_ACTION[entry.action].tone}>{AUDIT_ACTION[entry.action].label}</Badge></td>
                      <td>{entry.actor}</td>
                      <td className={styles.mono}>{entry.target}</td>
                      <td className={styles.muted}>{entry.detail || "—"}</td>
                      <td className={styles.mono}>{entry.ip ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <LoadMore hasMore={pages.hasNextPage} loading={pages.isFetchingNextPage} onMore={() => void pages.fetchNextPage()} shown={pages.items.length} />
          </>
        )}
      </Section>
    </>
  );
}

export function SecurityRoom() {
  const me = useAdminMe();
  const overview = useAdminQuery(["admin", "security", "overview"], fetchSecurityOverview, ROOM.pollMs);
  const blocks = useAdminQuery(["admin", "security", "ip-blocks"], fetchIpBlocks, ROOM.pollMs);
  const rules = useAdminQuery(["admin", "security", "access-rules"], fetchAccessRules, ROOM.pollMs);
  const mutations = useSecurityMutations();
  const ruleList = rules.data ?? [];
  const deniedDevices = ruleList.filter((r) => r.policy === "deny").length;
  const canOperate = me.data?.can_operate ?? false;
  const data = overview.data;

  const quickBlock = (alert: SecurityAlert) =>
    alert.ip && mutations.block.mutate({ ip: alert.ip, reason: alert.title, ttl_minutes: QUICK_BLOCK_MINUTES });

  return (
    <>
      <RoomHeader
        room={ROOM}
        updatedAt={overview.dataUpdatedAt}
        isFetching={overview.isFetching}
        isError={overview.isError}
        onRefresh={() => { void overview.refetch(); void blocks.refetch(); void rules.refetch(); }}
      />
      {overview.isError && !data && <RoomError error={overview.error} />}
      {data && (
        <>
          <StatStrip label="보안 요약 (최근 24시간)" items={summaryItems(data.summary)} />
          <AutoDefensePanel canOperate={canOperate} />
          <Tabs
            label="보안 감사 탭"
            tabs={[
              {
                key: "alerts", label: "알림", count: data.alerts.length,
                render: () => (
                  <AlertsPanel
                    alerts={data.alerts}
                    canOperate={canOperate}
                    onBlock={quickBlock}
                    pendingIp={mutations.block.isPending ? mutations.block.variables?.ip ?? null : null}
                  />
                ),
              },
              { key: "events", label: "이벤트", render: () => <EventsPanel /> },
              {
                key: "blacklist", label: "블랙리스트", count: (blocks.data?.length ?? 0) + deniedDevices,
                render: () => <BlacklistPanel blocks={blocks.data} rules={ruleList} canOperate={canOperate} mutations={mutations} />,
              },
              {
                key: "whitelist", label: "화이트리스트", count: ruleList.length - deniedDevices,
                render: () => <WhitelistPanel rules={ruleList} canOperate={canOperate} mutations={mutations} />,
              },
              { key: "audit", label: "감사 로그", render: () => <AuditPanel /> },
            ]}
          />
        </>
      )}
    </>
  );
}
