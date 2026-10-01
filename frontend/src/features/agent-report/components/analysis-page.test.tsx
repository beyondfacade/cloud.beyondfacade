import { StrictMode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AnalysisPage } from "./analysis-page";

let searchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({ useSearchParams: () => searchParams }));

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  listeners = new Map<string, (e: MessageEvent) => void>();
  close = vi.fn();
  onerror: (() => void) | null = null;
  constructor(public url: string) { FakeEventSource.instances.push(this); }
  addEventListener(type: string, listener: (e: MessageEvent) => void) { this.listeners.set(type, listener); }
  finish() {
    this.listeners.get("report_done")?.({ data: JSON.stringify({ type: "report_done", report_id: "r1", citations: [] }) } as MessageEvent);
  }
}

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  searchParams = new URLSearchParams();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  fetchMock = vi.fn(async (_url: string, init?: RequestInit) => Response.json(
    init?.method === "POST" ? { analysis_id: "a1" } : { region_code: "1168064000", name: "역삼1동", industry_id: "korean_food", cards: [] },
  ));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const page = <StrictMode><QueryClientProvider client={client}><AnalysisPage /></QueryClientProvider></StrictMode>;
  const view = render(page);
  return { ...view, navigate: () => view.rerender(<StrictMode><QueryClientProvider client={client}><AnalysisPage /></QueryClientProvider></StrictMode>) };
}
function postBodies() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST").map(([, init]) => JSON.parse(init.body));
}

it("URL의 동·업종·원 단위 예산으로 StrictMode에서도 분석을 한 번만 자동 시작한다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food&budget=50000000");
  renderPage();
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  expect(postBodies()).toEqual([{ region: "1168064000", industry: "korean_food", budget: 50000000 }]);
  expect(await screen.findByText("역삼1동 · 한식 · 예산 5,000만원")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/regions/1168064000/summary?industry=korean_food"), undefined);
  expect(screen.queryByRole("textbox", { name: "지역 코드" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "다시 분석" })).toBeDisabled();
});

it.each([null, "", "abc", "-1", "1.5", "Infinity", "9007199254740992"])("예산 %s는 본문과 요약에서 생략하고 자동 시작한다", async (budget) => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food");
  if (budget !== null) searchParams.set("budget", budget);
  renderPage();
  await waitFor(() => expect(postBodies()).toEqual([{ region: "1168064000", industry: "korean_food" }]));
  expect(await screen.findByText("역삼1동 · 한식")).toBeInTheDocument();
});

it("예산 0원도 생략하지 않고 보낸다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food&budget=0");
  renderPage();
  await waitFor(() => expect(postBodies()[0]?.budget).toBe(0));
  expect(await screen.findByText("역삼1동 · 한식 · 예산 0만원")).toBeInTheDocument();
});

it("완료 후 선택 질문을 입력해 같은 동·업종·예산으로 다시 분석한다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food&budget=50000000");
  renderPage();
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  act(() => FakeEventSource.instances[0].finish());
  fireEvent.click(screen.getByText("추가 질문 (선택)"));
  fireEvent.change(screen.getByLabelText("추가 질문"), { target: { value: "  임대료 상한은?  " } });
  fireEvent.click(screen.getByRole("button", { name: "다시 분석" }));
  await waitFor(() => expect(postBodies()).toHaveLength(2));
  expect(postBodies()[1]).toEqual({ region: "1168064000", industry: "korean_food", budget: 50000000, question: "임대료 상한은?" });
});

it.each(["", "region=1168064000", "industry=korean_food"])("파라미터가 불완전한 직접 방문에서는 자동 시작하지 않고 기존 폼을 유지한다 (%s)", (params) => {
  searchParams = new URLSearchParams(params);
  renderPage();
  expect(postBodies()).toEqual([]);
  expect(screen.getByRole("textbox", { name: "지역 코드" })).toHaveValue(searchParams.get("region") ?? "");
  expect(screen.getByRole("combobox", { name: "업종" })).toBeInTheDocument();
});

it("직접 방문 폼에서 동·업종을 고르면 수동 분석을 시작한다", async () => {
  renderPage();
  fireEvent.change(screen.getByRole("textbox", { name: "지역 코드" }), { target: { value: "1168064000" } });
  fireEvent.change(screen.getByRole("combobox", { name: "업종" }), { target: { value: "cafe" } });
  fireEvent.click(screen.getByRole("button", { name: /분석 시작/ }));
  await waitFor(() => expect(postBodies()).toEqual([{ region: "1168064000", industry: "cafe" }]));
});

it("동 이름 조회가 실패해도 코드로 요약하고 분석을 시작한다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food");
  fetchMock.mockImplementation(async (_url: string, init?: RequestInit) => init?.method === "POST"
    ? Response.json({ analysis_id: "a1" }) : Response.json({ error: { code: "NOT_FOUND", message: "조회 실패" } }, { status: 404 }));
  renderPage();
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  expect(screen.getByText("1168064000 · 한식")).toBeInTheDocument();
});

it("자동 시작 실패를 표시하고 다시 분석으로 재시도할 수 있다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food");
  let posts = 0;
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (_url: string, init?: RequestInit) => {
    if (init?.method !== "POST") return Response.json({ name: "역삼1동" });
    return ++posts === 1 ? Response.json({ error: { code: "UNAVAILABLE", message: "분석 일시 중단" } }, { status: 503 }) : Response.json({ analysis_id: "a1" });
  });
  renderPage();
  expect(await screen.findByRole("alert")).toHaveTextContent("분석 일시 중단");
  fireEvent.click(screen.getByRole("button", { name: "다시 분석" }));
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
});

it("URL 조건이 바뀌면 이전 스트림을 닫고 새 조건으로 자동 시작한다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food&budget=50000000");
  const { navigate } = renderPage();
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  searchParams = new URLSearchParams("region=1168065000&industry=cafe&budget=30000000");
  navigate();
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(2));
  expect(FakeEventSource.instances[0].close).toHaveBeenCalled();
  expect(postBodies()[1]).toEqual({ region: "1168065000", industry: "cafe", budget: 30000000 });
});

it("동 이름 조회를 기다리지 않고 자동 시작하며 질문 없는 재분석도 허용한다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food");
  fetchMock.mockImplementation((_url: string, init?: RequestInit) => init?.method === "POST"
    ? Promise.resolve(Response.json({ analysis_id: "a1" })) : new Promise(() => {}));
  renderPage();
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  expect(screen.getByText("1168064000 · 한식")).toBeInTheDocument();
  act(() => FakeEventSource.instances[0].finish());
  fireEvent.click(screen.getByRole("button", { name: "다시 분석" }));
  await waitFor(() => expect(postBodies()).toHaveLength(2));
  expect(postBodies()[1]).toEqual({ region: "1168064000", industry: "korean_food" });
});

it("원 단위 예산을 만원으로 표시할 때 소수 네 자리까지 보존한다", async () => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food&budget=50000001");
  renderPage();
  expect(await screen.findByText("역삼1동 · 한식 · 예산 5,000.0001만원")).toBeInTheDocument();
});

it("분석 화면 제목은 판정의 근거를 한 장으로 읽힌다", () => {
  renderPage();
  expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/판정의 근거를,\s*한 장으로\./);
});
