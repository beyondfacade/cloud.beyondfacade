"use client";

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import type { HealthcareSnapshot, ProbeKind, ProbeResult, UsageSummary } from "@/shared/api/types";
import { industryLabel } from "@/shared/industries";
import { fetchHealthcareSnapshot, runProbe } from "../api";
import { useAdminMe, useAdminQuery } from "../hooks/use-admin-query";
import { formatBytes, formatCount, formatDateTime, formatMs, percentOf } from "../lib/format";
import { ROOM_BY_KEY } from "../lib/rooms";
import { Badge, Empty, Notice, RoomError, Section, StatStrip, Tabs, type StatItem } from "./admin-ui";
import { RoomHeader } from "./room-header";
import styles from "./admin.module.css";

const ROOM = ROOM_BY_KEY.healthcare;

function overviewItems(data: HealthcareSnapshot): StatItem[] {
  const primary = data.llm_routes.find((r) => r.role === "primary");
  const missing = data.required_models.filter((m) => !m.installed).length;
  const embedded = percentOf(data.rag.embedded_chunks, data.rag.total_chunks);
  return [
    { label: "1차 LLM", value: primary?.available ? "가용" : "불가", tone: primary?.available ? "ok" : "danger", hint: primary?.model },
    { label: "Ollama", value: data.ollama.reachable ? "연결" : "끊김", tone: data.ollama.reachable ? "ok" : "danger", hint: formatMs(data.ollama.latency_ms) },
    { label: "필수 모델 누락", value: formatCount(missing), tone: missing ? "danger" : "ok" },
    { label: "분석 24h", value: formatCount(data.usage_24h.calls), hint: `p95 ${formatMs(data.usage_24h.p95_latency_ms)}` },
    { label: "RAG 임베딩", value: embedded == null ? "—" : `${embedded}%`, tone: embedded != null && embedded < 100 ? "warn" : "ok", hint: `${formatCount(data.rag.total_chunks)} 청크` },
  ];
}

function PipelinePanel({ data }: { data: HealthcareSnapshot }) {
  return (
    <>
      <Section title="분석 LLM 체인" aside={<p>1차 실패 시 폴백으로 넘어갑니다</p>} flush>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead><tr><th>역할</th><th>제공자</th><th>모델</th><th>상태</th><th>비고</th></tr></thead>
            <tbody>
              {data.llm_routes.map((route) => (
                <tr key={route.role}>
                  <td>{route.role === "primary" ? "1차" : "폴백"}</td>
                  <td>{route.provider}</td>
                  <td className={styles.mono}>{route.model}</td>
                  <td><Badge tone={route.available ? "ok" : "danger"} dot>{route.available ? "가용" : "불가"}</Badge></td>
                  <td className={styles.muted}>{route.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <div className={styles.grid2}>
        <Section title="필수 로컬 모델" flush>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>모델</th><th>용도</th><th>상태</th></tr></thead>
              <tbody>
                {data.required_models.map((model) => (
                  <tr key={model.name}>
                    <td className={styles.mono}>{model.name}</td>
                    <td>{model.purpose}</td>
                    <td>
                      {!model.installed ? (
                        <Badge tone="danger" dot>미설치</Badge>
                      ) : model.loaded ? (
                        <Badge tone="ok" dot>메모리 적재</Badge>
                      ) : (
                        <Badge dot>설치됨</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
        <Section title="Ollama 서버" aside={<p className={styles.mono}>{data.ollama.base_url}</p>} flush>
          {!data.ollama.reachable ? (
            <Empty>연결할 수 없습니다 — {data.ollama.error ?? "응답 없음"}</Empty>
          ) : !data.ollama.models.length ? (
            <Empty>설치된 모델이 없습니다.</Empty>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>설치 모델</th><th className={styles.num}>크기</th><th>적재</th></tr></thead>
                <tbody>
                  {data.ollama.models.map((model) => (
                    <tr key={model.name}>
                      <td className={styles.mono}>{model.name}</td>
                      <td className={styles.num}>{formatBytes(model.size_bytes)}</td>
                      <td>{data.ollama.loaded.includes(model.name) ? <Badge tone="ok">적재</Badge> : <span className={styles.muted}>—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      </div>
    </>
  );
}

const WINDOWS = [
  { key: "24h", label: "24시간", pick: (d: HealthcareSnapshot) => d.usage_24h },
  { key: "7d", label: "7일", pick: (d: HealthcareSnapshot) => d.usage_7d },
] as const;

function usageItems(usage: UsageSummary): StatItem[] {
  return [
    { label: "호출", value: formatCount(usage.calls) },
    { label: "입력 토큰", value: formatCount(usage.input_tokens) },
    { label: "출력 토큰", value: formatCount(usage.output_tokens) },
    { label: "지연 p50", value: formatMs(usage.p50_latency_ms) },
    { label: "지연 p95", value: formatMs(usage.p95_latency_ms) },
  ];
}

function UsagePanel({ data }: { data: HealthcareSnapshot }) {
  const [windowKey, setWindowKey] = useState<(typeof WINDOWS)[number]["key"]>("24h");
  const usage = (WINDOWS.find((w) => w.key === windowKey) ?? WINDOWS[0]).pick(data);
  return (
    <>
      <div className={styles.segment} role="group" aria-label="집계 기간">
        {WINDOWS.map((w) => (
          <button key={w.key} type="button" aria-pressed={w.key === windowKey} onClick={() => setWindowKey(w.key)}>{w.label}</button>
        ))}
      </div>
      <div className={styles.tabPanel}>
        <StatStrip label={`LLM 사용량 (${windowKey})`} items={usageItems(usage)} />
      </div>
      <Section title="모델별" flush>
        {!usage.by_model.length ? (
          <Empty>이 기간에 기록된 호출이 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>모델</th><th className={styles.num}>호출</th><th className={styles.num}>입력</th><th className={styles.num}>출력</th><th className={styles.num}>평균 지연</th></tr></thead>
              <tbody>
                {usage.by_model.map((m) => (
                  <tr key={m.model}>
                    <td className={styles.mono}>{m.model}</td>
                    <td className={styles.num}>{formatCount(m.calls)}</td>
                    <td className={styles.num}>{formatCount(m.input_tokens)}</td>
                    <td className={styles.num}>{formatCount(m.output_tokens)}</td>
                    <td className={styles.num}>{formatMs(m.avg_latency_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
      <Section title="최근 분석" flush>
        {!data.recent_analyses.length ? (
          <Empty>최근 분석 기록이 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>시각</th><th>행정동</th><th>업종</th><th>모델</th><th className={styles.num}>토큰(입/출)</th><th className={styles.num}>지연</th></tr></thead>
              <tbody>
                {data.recent_analyses.map((a) => (
                  <tr key={a.id}>
                    <td className={styles.muted}>{formatDateTime(a.created_at)}</td>
                    <td className={styles.mono}>{a.region_code}</td>
                    <td>{industryLabel(a.industry)}</td>
                    <td className={styles.mono}>{a.model}</td>
                    <td className={styles.num}>{formatCount(a.input_tokens)} / {formatCount(a.output_tokens)}</td>
                    <td className={styles.num}>{formatMs(a.latency_ms)}</td>
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

function RagPanel({ rag }: { rag: HealthcareSnapshot["rag"] }) {
  return (
    <div className={styles.grid2}>
      <Section title="출처별 청크" aside={<p>총 {formatCount(rag.total_chunks)} · 임베딩 {formatCount(rag.embedded_chunks)}</p>} flush>
        {!rag.by_source.length ? (
          <Empty>색인된 청크가 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>출처</th><th className={styles.num}>청크</th><th className={styles.num}>임베딩</th><th>최신 원문</th></tr></thead>
              <tbody>
                {rag.by_source.map((s) => (
                  <tr key={s.source_type}>
                    <td>{s.source_type}</td>
                    <td className={styles.num}>{formatCount(s.chunks)}</td>
                    <td className={styles.num}>
                      {s.embedded < s.chunks ? <Badge tone="warn">{formatCount(s.embedded)}</Badge> : formatCount(s.embedded)}
                    </td>
                    <td className={styles.muted}>{formatDateTime(s.latest_published_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
      <Section title="임베딩 모델" aside={<p>모델이 섞이면 검색 품질이 흔들립니다</p>} flush>
        {!rag.embedded_by.length ? (
          <Empty>임베딩된 청크가 없습니다.</Empty>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr><th>모델</th><th className={styles.num}>청크</th></tr></thead>
              <tbody>
                {rag.embedded_by.map((e) => (
                  <tr key={e.model}>
                    <td className={styles.mono}>{e.model}</td>
                    <td className={styles.num}>{formatCount(e.chunks)}</td>
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

const PROBE_KINDS: { key: ProbeKind; label: string; placeholder: string }[] = [
  { key: "rag", label: "RAG 검색", placeholder: "예: 강남구 카페 임대료 동향" },
  { key: "llm", label: "LLM 한 턴", placeholder: "예: 한 문장으로 자기소개 해줘" },
];

function ProbeOutcome({ result }: { result: ProbeResult }) {
  const meta = [formatMs(result.latency_ms), result.model, result.input_tokens != null ? `토큰 ${result.input_tokens}/${result.output_tokens}` : null]
    .filter(Boolean)
    .join(" · ");
  return (
    <div aria-live="polite">
      <p className={result.ok ? styles.formOk : styles.formError}>{result.ok ? "성공" : "실패"} — {meta}</p>
      {result.error && <p className={styles.probeOut}>{result.error}</p>}
      {result.output && <p className={styles.probeOut}>{result.output}</p>}
      {result.kind === "rag" && result.ok && (
        result.hits.length ? (
          <ol className={styles.hits}>
            {result.hits.map((hit) => (
              <li key={`${hit.source_type}-${hit.source_id}`} className={styles.hit}>
                <span className={styles.hitScore}>{hit.score.toFixed(3)}</span>
                <span>
                  <Badge>{hit.source_type}</Badge> {hit.snippet}
                </span>
              </li>
            ))}
          </ol>
        ) : <Empty>일치하는 청크가 없습니다.</Empty>
      )}
    </div>
  );
}

function ProbePanel({ canOperate }: { canOperate: boolean }) {
  const [kind, setKind] = useState<ProbeKind>("rag");
  const [message, setMessage] = useState("");
  const probe = useMutation({ mutationFn: () => runProbe(kind, message.trim()) });
  const current = PROBE_KINDS.find((k) => k.key === kind) ?? PROBE_KINDS[0];

  if (!canOperate) {
    return <Notice>프로브는 실제 LLM·임베딩 호출 비용이 들어 운영 관리자만 실행할 수 있습니다.</Notice>;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (message.trim()) probe.mutate();
  }

  return (
    <Section title="파이프라인 프로브" aside={<p>실제 체인을 한 번 호출해 응답을 확인합니다</p>}>
      <form onSubmit={submit} aria-label="프로브 실행">
        <div className={styles.form}>
          <div className={styles.segment} role="group" aria-label="프로브 종류">
            {PROBE_KINDS.map((k) => (
              <button key={k.key} type="button" aria-pressed={k.key === kind} onClick={() => { setKind(k.key); probe.reset(); }}>{k.label}</button>
            ))}
          </div>
        </div>
        <label className={`${styles.field} ${styles.fullRow}`}>
          <span className="sr-only">질의</span>
          <textarea
            className={styles.textarea}
            value={message}
            maxLength={500}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={current.placeholder}
            aria-label="프로브 질의"
          />
        </label>
        <div className={styles.form}>
          <button type="submit" className={styles.primaryButton} disabled={probe.isPending || !message.trim()}>
            {probe.isPending ? "호출 중…" : "프로브 실행"}
          </button>
        </div>
      </form>
      {probe.isError && <p className={styles.formError} role="alert">{probe.error instanceof Error ? probe.error.message : "프로브 실패"}</p>}
      {probe.data && <ProbeOutcome result={probe.data} />}
    </Section>
  );
}

export function HealthcareRoom() {
  const me = useAdminMe();
  const snapshot = useAdminQuery(["admin", "healthcare", "snapshot"], fetchHealthcareSnapshot, ROOM.pollMs);
  const data = snapshot.data;
  const canOperate = me.data?.can_operate ?? false;

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
          <StatStrip label="AI 파이프라인 요약" items={overviewItems(data)} />
          <Tabs
            label="헬스케어 탭"
            tabs={[
              { key: "pipeline", label: "개요", render: () => <PipelinePanel data={data} /> },
              { key: "usage", label: "사용량", render: () => <UsagePanel data={data} /> },
              { key: "rag", label: "RAG", render: () => <RagPanel rag={data.rag} /> },
              { key: "probe", label: "프로브", render: () => <ProbePanel canOperate={canOperate} /> },
            ]}
          />
        </>
      )}
    </>
  );
}
