import { afterEach, expect, it, vi } from "vitest";
import type { AgentEvent } from "@/shared/api/types";
import {
  alternativesOf, commerceChangeDetailOf, fundingCandidatesOf, hourGapOf,
  LATEST_PROFILE_QUARTER, metricRows, regionProfileOf, verdictOf,
} from "../../../fixtures";
import { GET } from "./route";

afterEach(() => vi.useRealTimers());

async function readEvents() {
  vi.useFakeTimers();
  const response = await GET(new Request("http://test/api/mock/analysis/a1/events"));
  expect(response.status).toBe(200);
  expect(response.headers.get("Content-Type")).toBe("text/event-stream");
  const body = response.text();
  await vi.runAllTimersAsync();
  const frames = (await body).trim().split("\n\n");
  const events = frames.map((frame) => {
    const [event, data] = frame.split("\n");
    const parsed: AgentEvent = JSON.parse(data.slice("data: ".length));
    expect(event).toBe(`event: ${parsed.type}`);
    return parsed;
  });
  return events;
}

it("SSE는 사실 수집 후 작성하고 작성과 오케스트레이터 완료 뒤 리포트를 완료한다", async () => {
  const events = await readEvents();
  expect(events.slice(0, 5)).toEqual([
    { type: "agent_status", agent: "orchestrator", status: "running" },
    { type: "agent_status", agent: "facts", status: "running" },
    { type: "facts", facts: expect.any(Object) },
    { type: "agent_status", agent: "facts", status: "done" },
    { type: "agent_status", agent: "writer", status: "running" },
  ]);
  expect(events.slice(5, -3).every((e) => e.type === "report_delta")).toBe(true);
  expect(events.slice(-3)).toEqual([
    { type: "agent_status", agent: "writer", status: "done" },
    { type: "agent_status", agent: "orchestrator", status: "done" },
    { type: "report_done", report_id: expect.any(String), citations: expect.any(Array) },
  ]);
});

it("SSE 사실은 계약의 13개 키와 기존 결정적 픽스처를 담는다", async () => {
  const events = await readEvents();
  const event = events.find((e) => e.type === "facts");
  expect(event).toBeDefined();
  if (!event) throw new Error("facts 이벤트 없음");
  const facts = event.facts;
  expect(Object.keys(facts).sort()).toEqual([
    "region", "verdict", "alternatives", "profile", "hour_gap", "commerce_change",
    "metrics_history", "population", "shocks", "analogs", "news", "funding_candidates", "budget",
  ].sort());
  if (!("code" in facts.region)) throw new Error("시연 지역 없음");
  const { code, industry_id } = facts.region;
  expect(facts.region).toEqual({ code: "1168064000", name: "역삼1동", industry_id: "cafe", industry_name: "카페" });
  expect(facts.verdict).toEqual(verdictOf(code, industry_id));
  expect(facts.alternatives).toEqual(alternativesOf(code, industry_id));
  expect(facts.profile).toEqual(regionProfileOf(code, LATEST_PROFILE_QUARTER));
  expect(facts.hour_gap).toEqual(hourGapOf(code, industry_id, "20254"));
  expect(facts.commerce_change).toEqual(commerceChangeDetailOf(code, LATEST_PROFILE_QUARTER));
  if (!Array.isArray(facts.funding_candidates)) throw new Error("지원사업 후보 없음");
  for (const candidate of facts.funding_candidates) {
    expect(candidate).not.toHaveProperty("target");
  }
  expect(facts.funding_candidates).toEqual(fundingCandidatesOf(null).map((candidate) => ({
    program_id: candidate.program_id, title: candidate.title, org: candidate.org,
    why: candidate.why, summary: candidate.summary, url: candidate.url,
    field_category: candidate.field_category, apply_period: candidate.apply_period,
    deadline: candidate.deadline,
  })));
  expect(facts.population).toEqual(expect.any(Object));
  expect(facts.shocks).toEqual(expect.any(Array));
  expect(facts.news).toEqual(expect.any(Array));
  expect(facts.budget).toBeNull();
  expect(events).toEqual(await readEvents());
});

it("SSE 충격은 시작일과 업종 관련 여부를 계약 키로 제공한다", async () => {
  const event = (await readEvents()).find((e) => e.type === "facts");
  expect(event?.facts.shocks).toEqual([expect.objectContaining({
    event_id: expect.any(String), name: "원두 가격 상승",
    start_date: "2026-09-01", industry_specific: true,
  })]);
});

it("SSE 연도별 이력은 2019년부터 최신까지 기존 지표와 개폐업 수를 담는다", async () => {
  const event = (await readEvents()).find((e) => e.type === "facts");
  if (!event || !Array.isArray(event.facts.metrics_history)) throw new Error("연도별 사실 없음");
  const history = event.facts.metrics_history;
  expect(history.map((row) => row.year)).toEqual([2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]);
  for (const row of history) {
    expect(Object.keys(row).sort()).toEqual(["year", "store_count", "open_count", "close_count", "closure_rate", "growth_rate"].sort());
    for (const metric of ["store_count", "closure_rate", "growth_rate"] as const) {
      expect(row[metric]).toBe(metricRows(metric, row.year, "cafe").find((r) => r.region_code === "1168064000")?.value);
    }
    for (const count of [row.open_count, row.close_count]) {
      expect(Number.isInteger(count) && count >= 0).toBe(true);
    }
  }
});

it("SSE 유사 사례는 분기별 업종 흐름과 해석 주의사항을 계약 키로 제공한다", async () => {
  const event = (await readEvents()).find((e) => e.type === "facts");
  const analogs = event?.facts.analogs;
  if (!analogs || "available" in analogs) throw new Error("유사 사례 없음");
  expect(analogs.categories.map((c) => c.reason)).toEqual(["question", "current"]);
  expect(analogs.current_events.every((e) => e.current)).toBe(true);
  expect(analogs.analogs.length).toBeGreaterThan(0);
  for (const impact of [...analogs.current_events, ...analogs.analogs]) {
    expect(impact.quarters.length).toBeLessThanOrEqual(12);
    impact.quarters.forEach((q, index) => {
      expect(q.quarter).toBe(index + 1);
      expect(q.label).toMatch(/^[1-3]년 차 [1-4]분기$/);
      expect(q.start_month <= q.end_month).toBe(true);
    });
    expect(impact.series[0]).toMatchObject({ industry_id: "cafe", role: "target" });
    for (const series of impact.series) expect(series.values).toHaveLength(impact.quarters.length);
    expect(impact.target_weak_quarters + impact.target_strong_quarters).toBeLessThanOrEqual(impact.quarters.length);
  }
  expect(analogs.caveats.length).toBeGreaterThan(0);
});

it("SSE 문장 조각은 같은 섹션에 반복되고 이어 붙이면 여섯 제목과 본문이 완성된다", async () => {
  const deltas = (await readEvents()).filter((e) => e.type === "report_delta");
  const sections = [
    ["verdict", "판정"], ["reasons", "왜 안 되나"], ["analogs", "유사 사례"], ["conditions", "그래도 한다면"],
    ["alternatives", "대안 동네·업종"], ["funding", "대안 업종 지원사업"],
  ] as const;
  expect([...new Set(deltas.map((e) => e.section))]).toEqual([...sections.map(([section]) => section), "answer"]);
  for (const [section, title] of sections) {
    const chunks = deltas.filter((e) => e.section === section).map((e) => e.markdown);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((chunk) => chunk.trim().length > 0)).toBe(true);
    expect(chunks.every((chunk) => /[.!?]\s*$/.test(chunk))).toBe(true);
    const markdown = chunks.join("");
    expect(markdown.startsWith(`### ${title}\n\n`)).toBe(true);
    expect(markdown.slice(`### ${title}\n\n`.length).trim().length).toBeGreaterThan(0);
  }
});

it("SSE 해석은 여섯 사실 절 뒤에 한 번 오고 숫자를 담지 않는다", async () => {
  const events = await readEvents();
  const deltas = events.filter((e): e is Extract<AgentEvent, { type: "report_delta" }> => e.type === "report_delta");
  const answers = deltas.filter((e) => e.section === "answer");
  expect(answers).toHaveLength(1);
  expect(deltas.at(-1)).toEqual(answers[0]);
  expect(new Set(deltas.slice(0, -1).map((e) => e.section))).toEqual(
    new Set(["verdict", "reasons", "analogs", "conditions", "alternatives", "funding"]),
  );
  expect(answers[0].markdown).not.toMatch(/\d/);
});
