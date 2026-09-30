"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { FacilitySnapshot, HostPoint } from "@/shared/api/types";
import { fetchCollectorLog, fetchFacilitySnapshot, fetchHostHistory, runCollector } from "../api";
import { useAdminMe, useAdminQuery } from "../hooks/use-admin-query";
import { useSessionSeries } from "../hooks/use-session-series";
import {
  COLLECTOR_STATUS,
  TREND_WINDOWS,
  formatAxisTime,
  formatBytes,
  formatCount,
  formatDateTime,
  formatMs,
  formatRelative,
  formatUptime,
  percentOf,
  usageTone,
} from "../lib/format";
import { ROOM_BY_KEY } from "../lib/rooms";
import { TrendChart } from "./admin-charts";
import { Badge, Empty, errorMessage, Meter, RoomError, Section, Segment, Sparkline, StatStrip, Tabs, type StatItem } from "./admin-ui";
import { RoomHeader } from "./room-header";
import styles from "./admin.module.css";

const ROOM = ROOM_BY_KEY.facility;
const MB = 1024 ** 2;
/** 표본은 1분 간격 — 그보다 자주 물을 이유가 없다. */
const HISTORY_POLL_MS = 60_000;
const LOG_POLL_MS = 5_000;

function hostItems(data: FacilitySnapshot): StatItem[] {
  const down = data.services.filter((s) => !s.ok).length;
  const stale = data.collectors.filter((c) => c.status !== "ok").length;
  return [
    { label: "호스트", value: data.host.hostname, hint: data.host.platform, compact: true },
    { label: "가동 시간", value: formatUptime(data.host.uptime_seconds) },
    { label: "부하(1·5·15분)", value: data.host.load_avg.map((v) => v.toFixed(1)).join(" · ") || "—", hint: `${data.host.cpu_count}코어`, compact: true },
    { label: "서비스 장애", value: formatCount(down), tone: down ? "danger" : "ok" },
    { label: "수집 지연·누락", value: formatCount(stale), tone: stale ? "warn" : "ok" },
  ];
}

function DashboardPanel({ data, gpuSeries }: { data: FacilitySnapshot; gpuSeries: number[][] }) {
  const { host } = data;
  const memUsed = host.memory_total_bytes != null && host.memory_available_bytes != null
    ? host.memory_total_bytes - host.memory_available_bytes
    : null;
  const memPct = percentOf(memUsed, host.memory_total_bytes);
  const swapPct = percentOf(host.swap_used_bytes, host.swap_total_bytes);
  const cpuPct = host.cpu_percent == null ? null : Math.round(host.cpu_percent * 10) / 10;

  return (
    <>
      <Section title="자원 사용률" aside={<p>80% 주의 · 90% 위험</p>}>
        <div className={styles.meters}>
          <Meter label="CPU" percent={cpuPct} tone={usageTone(cpuPct)} detail={`${host.cpu_count}코어`} />
          <Meter label="메모리" percent={memPct} tone={usageTone(memPct)} detail={`${formatBytes(memUsed)} / ${formatBytes(host.memory_total_bytes)}`} />
          <Meter label="스왑" percent={swapPct} tone={usageTone(swapPct)} detail={`${formatBytes(host.swap_used_bytes)} / ${formatBytes(host.swap_total_bytes)}`} />
          {host.disks.map((disk) => {
            const pct = percentOf(disk.used_bytes, disk.total_bytes);
            return (
              <Meter
                key={disk.mount}
                label={`디스크 ${disk.mount}`}
                percent={pct}
                tone={usageTone(pct)}
                detail={`여유 ${formatBytes(disk.free_bytes)} / ${formatBytes(disk.total_bytes)}`}
              />
            );
          })}
        </div>
      </Section>
      <div className={styles.grid2}>
        <Section title="GPU" aside={<p>그래프는 이 화면을 연 뒤의 VRAM 추이</p>}>
          {!data.gpus.length ? (
            <Empty>감지된 GPU가 없습니다 (nvidia-smi 없음).</Empty>
          ) : (
            <div className={styles.meters}>
              {data.gpus.map((gpu, i) => {
                const pct = percentOf(gpu.memory_used_mb, gpu.memory_total_mb);
                return (
                  <div key={gpu.index}>
                    <Meter
                      label={`#${gpu.index} ${gpu.name} VRAM`}
                      percent={pct}
                      tone={usageTone(pct)}
                      detail={`${formatBytes(gpu.memory_used_mb * MB)} / ${formatBytes(gpu.memory_total_mb * MB)} · 사용률 ${gpu.utilization_percent}%${gpu.temperature_c != null ? ` · ${gpu.temperature_c}℃` : ""}`}
                    />
                    <Sparkline values={gpuSeries[i] ?? []} max={gpu.memory_total_mb} label={`GPU ${gpu.index} VRAM 추이`} />
                  </div>
                );
              })}
            </div>
          )}
        </Section>
        <Section title="서비스" flush>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>서비스</th><th>상태</th><th className={styles.num}>응답</th><th>상세</th></tr></thead>
              <tbody>
                {data.services.map((s) => (
                  <tr key={s.name}>
                    <td>{s.name}</td>
                    <td><Badge tone={s.ok ? "ok" : "danger"} dot>{s.ok ? "정상" : "장애"}</Badge></td>
                    <td className={styles.num}>{formatMs(s.latency_ms)}</td>
                    <td className={styles.muted}>{s.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </>
  );
}

const pct = (v: number | null) => (v == null ? "—" : `${v}%`);

function TrendPanel() {
  const [hours, setHours] = useState(24);
  const history = useAdminQuery(["admin", "facility", "history", hours], () => fetchHostHistory(hours), HISTORY_POLL_MS);
  const points = history.data?.points ?? [];
  const labels = points.map((p) => formatAxisTime(p.t, hours));
  const col = (pick: (p: HostPoint) => number | null) => points.map(pick);
  const hasGpu = points.some((p) => p.gpu_util_percent != null);

  return (
    <>
      <div className={styles.toolbar}>
        <Segment label="추세 기간" options={TREND_WINDOWS.map((w) => ({ value: w.hours, label: w.label }))} value={hours} onChange={setHours} />
        {history.data && <span className={styles.muted}>{Math.round(history.data.bucket_seconds / 60)}분 평균 · {points.length}점</span>}
      </div>
      {history.isError ? (
        <RoomError error={history.error} />
      ) : !points.length ? (
        <Section title="호스트 추세">
          <Empty>{history.isPending ? "불러오는 중…" : "표본이 없습니다 — host-metrics-sampler 크론이 매분 기록합니다."}</Empty>
        </Section>
      ) : (
        <div className={styles.grid2}>
          <Section title="호스트 자원" aside={<p>백분율 · 8일 보존</p>}>
            <TrendChart
              label="CPU·메모리·디스크 사용률" labels={labels} max={100} format={pct}
              series={[
                { key: "cpu", label: "CPU", tone: "accent", values: col((p) => p.cpu_percent) },
                { key: "memory", label: "메모리", tone: "warn", values: col((p) => p.memory_percent) },
                { key: "disk", label: "디스크", tone: "muted", values: col((p) => p.disk_percent) },
                { key: "swap", label: "스왑", tone: "muted", dashed: true, values: col((p) => p.swap_percent) },
              ]}
            />
            <TrendChart
              label="부하 평균(1분)" labels={labels} format={(v) => (v == null ? "—" : v.toFixed(2))}
              series={[{ key: "load1", label: "load1", tone: "accent", values: col((p) => p.load1) }]}
            />
          </Section>
          <Section title="GPU">
            {!hasGpu ? <Empty>기록된 GPU 표본이 없습니다.</Empty> : (
              <>
                <TrendChart
                  label="GPU 사용률·VRAM" labels={labels} max={100} format={pct}
                  series={[
                    { key: "util", label: "사용률", tone: "accent", values: col((p) => p.gpu_util_percent) },
                    { key: "vram", label: "VRAM", tone: "warn", values: col((p) => p.gpu_memory_percent) },
                  ]}
                />
                <TrendChart
                  label="GPU 온도" labels={labels} format={(v) => (v == null ? "—" : `${v}℃`)}
                  series={[{ key: "temp", label: "온도", tone: "danger", values: col((p) => p.gpu_temp_c) }]}
                />
              </>
            )}
          </Section>
        </div>
      )}
    </>
  );
}

const LOG_LINE_OPTIONS = [100, 200, 500, 1_000];

function CollectorLogSection({ collector, onClose }: { collector: FacilitySnapshot["collectors"][number]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [lines, setLines] = useState(200);
  const log = useAdminQuery(
    ["admin", "facility", "collector-log", collector.key, lines],
    () => fetchCollectorLog(collector.key, lines),
    LOG_POLL_MS,
  );
  const run = useMutation({
    mutationFn: () => runCollector(collector.key),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin", "facility"] }),
  });
  const running = log.data?.running ?? false;
  const logBox = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (logBox.current) logBox.current.scrollTop = logBox.current.scrollHeight;
  }, [log.data]);

  return (
    <Section
      title={`${collector.label} 로그`}
      aside={(
        <div className={styles.form}>
          {running && <Badge tone="warn" dot>실행 중</Badge>}
          <label className={styles.field}>
            <span className="sr-only">줄 수</span>
            <select className={styles.select} value={lines} onChange={(e) => setLines(Number(e.target.value))} aria-label="줄 수">
              {LOG_LINE_OPTIONS.map((n) => <option key={n} value={n}>마지막 {n}줄</option>)}
            </select>
          </label>
          <button type="button" className={styles.primaryButton} onClick={() => run.mutate()} disabled={run.isPending || running}>
            {run.isPending ? "시작 중…" : "지금 실행"}
          </button>
          <button type="button" className={styles.ghostButton} onClick={onClose}>닫기</button>
        </div>
      )}
      flush
    >
      {run.isError && <p className={`${styles.formError} ${styles.sectionBody}`} role="alert">{errorMessage(run.error, "실행하지 못했습니다")}</p>}
      {run.isSuccess && <p className={`${styles.formOk} ${styles.sectionBody}`} role="status">{formatDateTime(run.data.started_at)}에 실행을 시작했습니다.</p>}
      {log.isError ? (
        <RoomError error={log.error} />
      ) : !log.data ? (
        <Empty>불러오는 중…</Empty>
      ) : !log.data.lines.length ? (
        <Empty>로그가 비어 있습니다 ({log.data.log_file}).</Empty>
      ) : (
        <pre ref={logBox} className={styles.logBox} aria-label={`${collector.key} 로그`}>{log.data.lines.join("\n")}</pre>
      )}
    </Section>
  );
}

function CollectorsPanel({ collectors, now, canOperate }: { collectors: FacilitySnapshot["collectors"]; now: number; canOperate: boolean }) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const open = collectors.find((c) => c.key === openKey);
  return (
    <>
      <Section
        title="수집기 데이터 신선도"
        aside={<p>주기의 1.5배를 넘기면 지연{canOperate ? "" : " · 로그·수동 실행은 운영 관리자 전용"}</p>}
        flush
      >
        {!collectors.length ? (
          <Empty>등록된 수집기가 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>수집기</th><th>주기</th><th>상태</th><th>마지막 실행</th><th>테이블</th><th className={styles.num}>행</th><th>최신 데이터</th>
                  {canOperate && <th>도구</th>}
                </tr>
              </thead>
              <tbody>
                {collectors.map((c) => (
                  <tr key={c.key} className={c.key === openKey ? styles.rowSelected : undefined}>
                    <td>{c.label}<br /><span className={`${styles.muted} ${styles.mono}`}>{c.key}</span></td>
                    <td className={styles.muted}>{c.schedule}</td>
                    <td><Badge tone={COLLECTOR_STATUS[c.status].tone} dot>{COLLECTOR_STATUS[c.status].label}</Badge></td>
                    <td>{formatRelative(c.last_run_at, now)}</td>
                    <td className={styles.mono}>{c.table ?? "—"}</td>
                    <td className={styles.num}>{formatCount(c.rows)}</td>
                    <td className={styles.muted}>{formatDateTime(c.latest_data_at)}</td>
                    {canOperate && (
                      <td>
                        <button
                          type="button" className={styles.ghostButton} aria-label={`${c.label} 로그`}
                          aria-pressed={c.key === openKey} onClick={() => setOpenKey(c.key === openKey ? null : c.key)}
                        >
                          로그·실행
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
      {canOperate && open && <CollectorLogSection key={open.key} collector={open} onClose={() => setOpenKey(null)} />}
    </>
  );
}

function DatabasePanel({ database }: { database: FacilitySnapshot["database"] }) {
  if (!database) return <Section title="데이터베이스"><Empty>데이터베이스에 연결할 수 없습니다.</Empty></Section>;
  const connPct = percentOf(database.connections, database.max_connections);
  return (
    <div className={styles.grid2}>
      <Section title="PostgreSQL">
        <div className={styles.meters}>
          <Meter label="연결" percent={connPct} tone={usageTone(connPct)} detail={`${database.connections} / ${database.max_connections}`} />
        </div>
        <table className={styles.table}>
          <tbody>
            <tr><td className={styles.muted}>버전</td><td>{database.version}</td></tr>
            <tr><td className={styles.muted}>DB 크기</td><td>{formatBytes(database.size_bytes)}</td></tr>
            <tr><td className={styles.muted}>마이그레이션</td><td className={styles.mono}>{database.alembic_revision ?? "—"}</td></tr>
            <tr><td className={styles.muted}>pgvector</td><td>{database.pgvector_version ?? <Badge tone="danger">미설치</Badge>}</td></tr>
          </tbody>
        </table>
      </Section>
      <Section title="큰 테이블" flush>
        {!database.largest_tables.length ? (
          <Empty>테이블 통계가 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>테이블</th><th className={styles.num}>크기</th><th className={styles.num}>행(추정)</th></tr></thead>
              <tbody>
                {database.largest_tables.map((t) => (
                  <tr key={t.name}>
                    <td className={styles.mono}>{t.name}</td>
                    <td className={styles.num}>{formatBytes(t.total_bytes)}</td>
                    <td className={styles.num}>{formatCount(t.row_estimate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

export function FacilityRoom() {
  const me = useAdminMe();
  const canOperate = me.data?.can_operate ?? false;
  const snapshot = useAdminQuery(["admin", "facility", "snapshot"], fetchFacilitySnapshot, ROOM.pollMs);
  const data = snapshot.data;
  const gpuSeries = useSessionSeries(data?.gpus.map((g) => g.memory_used_mb), snapshot.dataUpdatedAt);
  // 상대 시각 기준점 — 스냅샷 생성 시각을 쓰면 렌더가 결정적이다(서버 시계 기준).
  const now = data ? Date.parse(data.generated_at) : 0;

  return (
    <>
      <RoomHeader
        room={ROOM}
        updatedAt={snapshot.dataUpdatedAt}
        isFetching={snapshot.isFetching}
        isError={snapshot.isError}
        onRefresh={() => void snapshot.refetch()}
      />
      {snapshot.isError && !data && <RoomError error={snapshot.error} />}
      {data && (
        <>
          <StatStrip label="설비 요약" items={hostItems(data)} />
          <Tabs
            label="설비 탭"
            tabs={[
              { key: "dashboard", label: "대시보드", render: () => <DashboardPanel data={data} gpuSeries={gpuSeries} /> },
              { key: "trends", label: "추세", render: () => <TrendPanel /> },
              {
                key: "collectors", label: "수집기", count: data.collectors.filter((c) => c.status !== "ok").length || undefined,
                render: () => <CollectorsPanel collectors={data.collectors} now={now} canOperate={canOperate} />,
              },
              { key: "database", label: "데이터베이스", render: () => <DatabasePanel database={data.database} /> },
            ]}
          />
        </>
      )}
    </>
  );
}
