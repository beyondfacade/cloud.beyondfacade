"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import type { IpBlock, IpBlockCreate, SecurityAlert, SecurityOverview } from "@/shared/api/types";
import { createIpBlock, deleteIpBlock, fetchIpBlocks, fetchSecurityOverview } from "../api";
import { useAdminMe, useAdminQuery } from "../hooks/use-admin-query";
import { BLOCK_TTL_OPTIONS, EVENT_KIND, SEVERITY, formatCount, formatDateTime } from "../lib/format";
import { ROOM_BY_KEY } from "../lib/rooms";
import { Badge, Empty, Notice, RoomError, Section, StatStrip, Tabs, type StatItem } from "./admin-ui";
import { RoomHeader } from "./room-header";
import styles from "./admin.module.css";

const ROOM = ROOM_BY_KEY.security;
const QUICK_BLOCK_MINUTES = 1_440;

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

function useSecurityMutations() {
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "security"] });
  const block = useMutation({ mutationFn: (body: IpBlockCreate) => createIpBlock(body), onSuccess: refresh });
  const unblock = useMutation({ mutationFn: (ip: string) => deleteIpBlock(ip), onSuccess: refresh });
  return { block, unblock };
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

function EventsPanel({ events }: { events: SecurityOverview["recent_events"] }) {
  return (
    <Section title="최근 접근 이벤트" aside={<p>최근 50건</p>} flush>
      {!events.length ? (
        <Empty>기록된 이벤트가 없습니다.</Empty>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr><th>시각</th><th>종류</th><th>IP</th><th>요청</th><th className={styles.num}>상태</th><th>계정</th></tr>
            </thead>
            <tbody>
              {events.map((event, index) => (
                <tr key={event.id ?? `${event.occurred_at}-${index}`}>
                  <td className={styles.muted}>{formatDateTime(event.occurred_at)}</td>
                  <td><Badge tone={EVENT_KIND[event.kind].tone}>{EVENT_KIND[event.kind].label}</Badge></td>
                  <td className={styles.mono}>{event.ip ?? "—"}</td>
                  <td className={styles.mono}>{event.method} {event.path}</td>
                  <td className={styles.num}>{event.status_code}</td>
                  <td>{event.username ?? <span className={styles.muted}>—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

function BlockForm({ onSubmit, isPending, error }: {
  onSubmit: (body: IpBlockCreate) => void;
  isPending: boolean;
  error: unknown;
}) {
  const [ip, setIp] = useState("");
  const [reason, setReason] = useState("");
  const [ttl, setTtl] = useState<number | null>(QUICK_BLOCK_MINUTES);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!ip.trim()) return;
    onSubmit({ ip: ip.trim(), reason: reason.trim(), ttl_minutes: ttl });
    setIp("");
    setReason("");
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-label="IP 차단 추가">
      <label className={styles.field}>
        IP 주소
        <input className={styles.input} value={ip} onChange={(e) => setIp(e.target.value)} placeholder="203.0.113.10" required />
      </label>
      <label className={`${styles.field} ${styles.fieldGrow}`}>
        사유
        <input className={styles.input} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="수동 차단" />
      </label>
      <label className={styles.field}>
        기간
        <select
          className={styles.select}
          value={ttl ?? "forever"}
          onChange={(e) => setTtl(e.target.value === "forever" ? null : Number(e.target.value))}
        >
          {BLOCK_TTL_OPTIONS.map((option) => (
            <option key={option.label} value={option.minutes ?? "forever"}>{option.label}</option>
          ))}
        </select>
      </label>
      <button type="submit" className={styles.primaryButton} disabled={isPending}>차단 추가</button>
      {error instanceof Error && <p className={`${styles.formError} ${styles.fullRow}`} role="alert">{error.message}</p>}
    </form>
  );
}

function BlocksPanel({ blocks, canOperate, mutations }: {
  blocks: IpBlock[] | undefined;
  canOperate: boolean;
  mutations: ReturnType<typeof useSecurityMutations>;
}) {
  const { block, unblock } = mutations;
  return (
    <>
      {canOperate ? (
        <Section title="차단 추가">
          <BlockForm onSubmit={(body) => block.mutate(body)} isPending={block.isPending} error={block.error} />
        </Section>
      ) : (
        <Notice>조회 관리자는 차단 목록을 볼 수만 있습니다. 차단·해제는 운영 관리자 권한이 필요합니다.</Notice>
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
                    <td>{b.expires_at ? formatDateTime(b.expires_at) : <Badge tone="warn">무기한</Badge>}</td>
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
    </>
  );
}

export function SecurityRoom() {
  const me = useAdminMe();
  const overview = useAdminQuery(["admin", "security", "overview"], fetchSecurityOverview, ROOM.pollMs);
  const blocks = useAdminQuery(["admin", "security", "ip-blocks"], fetchIpBlocks, ROOM.pollMs);
  const mutations = useSecurityMutations();
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
        onRefresh={() => { void overview.refetch(); void blocks.refetch(); }}
      />
      {overview.isError && !data && <RoomError error={overview.error} />}
      {data && (
        <>
          <StatStrip label="보안 요약 (최근 24시간)" items={summaryItems(data.summary)} />
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
              { key: "events", label: "이벤트", count: data.recent_events.length, render: () => <EventsPanel events={data.recent_events} /> },
              {
                key: "blocks", label: "IP 차단", count: blocks.data?.length,
                render: () => <BlocksPanel blocks={blocks.data} canOperate={canOperate} mutations={mutations} />,
              },
            ]}
          />
        </>
      )}
    </>
  );
}
