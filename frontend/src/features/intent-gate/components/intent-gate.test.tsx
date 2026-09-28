import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { IntentResult } from "@/shared/api/types";
import { IntentGate } from "./intent-gate";
import { AUTO_NAVIGATE_MS } from "./diagnosis-line";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const api = vi.hoisted(() => ({
  parseIntent: vi.fn(),
  diagnoseIntent: vi.fn(),
  fetchRegionList: vi.fn(),
}));
vi.mock("../api", () => api);

function result(overrides: Partial<IntentResult>): IntentResult {
  return {
    intent_type: "C",
    region_code: null,
    region_name: null,
    district_code: null,
    industry_id: null,
    budget_krw: null,
    missing: [],
    candidates: [],
    diagnosis: null,
    source: "rule",
    ...overrides,
  };
}

const DIAGNOSIS = {
  type_code: "office", type_name: "낮 인구 우위형", time_label: "day", peak_sales_band: "11_14",
  sentence: "역삼1동은 낮 인구 우위형이고, 카페는 점심(11~14시)에 돈이 돕니다.",
  year_quarter: "20262", hour_gap_quarter: "20254",
};

async function submit(text: string) {
  fireEvent.change(screen.getByLabelText("어느 동네에서 무엇을 하려고 하세요?"), { target: { value: text } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /찾아보기|찾는 중/ })); });
}

beforeEach(() => {
  router.push.mockReset();
  api.parseIntent.mockReset();
  api.diagnoseIntent.mockReset();
  api.fetchRegionList.mockReset();
});
afterEach(() => vi.useRealTimers());

describe("관문 상태 전이", () => {
  it("동 목록이 일시 실패하면 같은 구를 재시도하여 동을 고를 수 있다", async () => {
    api.parseIntent.mockResolvedValue(result({ district_code: "11680", industry_id: "cafe", budget_krw: 50_000_000 }));
    api.fetchRegionList.mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce([{ region_code: "1168064000", name: "역삼1동" }]);
    api.diagnoseIntent.mockResolvedValue(result({ diagnosis: null }));
    render(<IntentGate />);

    await submit("강남구 카페, 예산 5천");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText("강남구의 어느 동인가요?")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(await screen.findByRole("button", { name: "역삼1동" })).toBeInTheDocument();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "역삼1동" })); });
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/map?region=1168064000&industry=cafe&budget=50000000"));
  });

  it("선택한 구의 동 목록이 비어 있으면 재시도에서 새 목록을 받는다", async () => {
    api.parseIntent.mockResolvedValue(result({ district_code: "11680", industry_id: "cafe" }));
    api.fetchRegionList.mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ region_code: "1168064000", name: "역삼1동" }]);
    render(<IntentGate />);

    await submit("강남구 카페");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(await screen.findByRole("button", { name: "역삼1동" })).toBeInTheDocument();
  });

  it("파싱 실패 뒤 입력을 유지하고 재시도할 수 있다", async () => {
    api.parseIntent.mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce(result({ industry_id: "gym" }));
    render(<IntentGate />);

    await submit("헬스장");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText("어느 동네에서 무엇을 하려고 하세요?")).toHaveValue("헬스장");
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(await screen.findByText(/말씀하신 곳을 찾지 못했어요/)).toBeInTheDocument();
  });

  it("파싱 실패 뒤 직접 동네를 고르거나 지도로 갈 수 있다", async () => {
    api.parseIntent.mockRejectedValue(new Error("offline"));
    api.fetchRegionList.mockResolvedValue([{ region_code: "1168064000", name: "역삼1동" }]);
    render(<IntentGate />);

    await submit("역삼동에 카페");
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "동네 직접 고르기" }));
    expect(await screen.findByRole("button", { name: "강남구" })).toBeInTheDocument();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "강남구" })); });
    expect(await screen.findByRole("button", { name: "역삼1동" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "아직 몰라요 — 지도에서 고를게요" }));
    expect(router.push).toHaveBeenCalledWith("/map");
  });

  it("파싱이 응답하지 않아도 15초 뒤 재시도할 수 있다", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.parseIntent.mockImplementation(() => new Promise(() => {}));
    render(<IntentGate />);

    await submit("헬스장");
    expect(screen.getByRole("button", { name: /찾는 중/ })).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(15_001); });
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });

  it("선택한 구의 동 목록이 응답하지 않아도 15초 뒤 실패를 알린다", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.parseIntent.mockResolvedValue(result({ district_code: "11680", industry_id: "cafe" }));
    api.fetchRegionList.mockImplementation(() => new Promise(() => {}));
    render(<IntentGate />);

    await submit("강남구 카페");
    await act(async () => { vi.advanceTimersByTime(15_001); });
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "동네 직접 고르기" })).toBeInTheDocument();
  });

  it("선택적 진단이 느리면 3초 뒤 예산을 포함한 지도로 간다", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.parseIntent.mockResolvedValue(result({
      intent_type: "A", region_code: "1168064000", industry_id: "cafe", budget_krw: 50_000_000,
    }));
    api.diagnoseIntent.mockImplementation(() => new Promise(() => {}));
    render(<IntentGate />);

    await submit("역삼1동 카페 예산 5천");
    await act(async () => { vi.advanceTimersByTime(3_001); });
    expect(router.push).toHaveBeenCalledWith("/map?region=1168064000&industry=cafe&budget=50000000");
  });

  it("새 검색이 시작되면 이전 응답이 화면과 이동을 덮지 않는다", async () => {
    let resolveFirst!: (value: IntentResult) => void;
    api.parseIntent.mockImplementationOnce(() => new Promise<IntentResult>((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValueOnce(result({ industry_id: "gym" }));
    render(<IntentGate />);

    await submit("첫 검색");
    await submit("헬스장");
    expect(await screen.findByText(/말씀하신 곳을 찾지 못했어요/)).toBeInTheDocument();
    await act(async () => { resolveFirst(result({ intent_type: "A", region_code: "1168064000", industry_id: "cafe", diagnosis: DIAGNOSIS })); });
    expect(screen.getByText(/말씀하신 곳을 찾지 못했어요/)).toBeInTheDocument();
    expect(screen.queryByText(DIAGNOSIS.sentence)).toBeNull();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("이전 진단의 자동 이동은 새 검색을 덮지 않는다", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.parseIntent.mockResolvedValueOnce(result({
      intent_type: "A", region_code: "1168064000", industry_id: "cafe", diagnosis: DIAGNOSIS,
    })).mockResolvedValueOnce(result({ industry_id: "gym" }));
    render(<IntentGate />);

    await submit("역삼1동 카페");
    expect(await screen.findByText(DIAGNOSIS.sentence)).toBeInTheDocument();
    await submit("헬스장");
    expect(await screen.findByText(/말씀하신 곳을 찾지 못했어요/)).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(AUTO_NAVIGATE_MS + 10); });
    expect(router.push).not.toHaveBeenCalled();
  });

  it("A유형이면 진단 문장을 보여주고 잠시 뒤 지도로 간다", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.parseIntent.mockResolvedValue(result({
      intent_type: "A", region_code: "1168064000", region_name: "역삼1동", district_code: "11680",
      industry_id: "cafe", budget_krw: 50_000_000, diagnosis: DIAGNOSIS,
    }));
    render(<IntentGate />);

    await submit("역삼1동에 카페, 예산 5천");

    expect(await screen.findByText(DIAGNOSIS.sentence)).toBeInTheDocument();
    expect(router.push).not.toHaveBeenCalled();
    await act(async () => { vi.advanceTimersByTime(AUTO_NAVIGATE_MS + 10); });
    expect(router.push).toHaveBeenCalledWith("/map?region=1168064000&industry=cafe&budget=50000000");
  });

  it("후보가 여럿이면 후보 칩으로 되묻고, 고르면 진단을 받아 이어간다 (주 경로)", async () => {
    api.parseIntent.mockResolvedValue(result({
      intent_type: "C", industry_id: "cafe", budget_krw: 50_000_000, missing: ["region"],
      candidates: [
        { region_code: "1168064000", region_name: "역삼1동", district_code: "11680", district_name: "강남구" },
        { region_code: "1168065000", region_name: "역삼2동", district_code: "11680", district_name: "강남구" },
      ],
    }));
    api.diagnoseIntent.mockResolvedValue(result({ intent_type: "A", region_code: "1168064000", industry_id: "cafe", diagnosis: DIAGNOSIS }));
    render(<IntentGate />);

    await submit("역삼동에 카페, 예산 5천");
    expect(await screen.findByText(/같은 이름의 동이 여럿/)).toBeInTheDocument();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "강남구 역삼1동" })); });

    expect(api.diagnoseIntent).toHaveBeenCalledWith("1168064000", "cafe", expect.any(AbortSignal));
    expect(await screen.findByText(DIAGNOSIS.sentence)).toBeInTheDocument();
  });

  it("동만 잡히면 업종 칩으로 되묻고, 우회로를 고르면 B유형으로 바로 착지한다", async () => {
    api.parseIntent.mockResolvedValue(result({
      intent_type: "B", region_code: "1144071000", region_name: "연남동", district_code: "11440", missing: ["industry", "budget"],
    }));
    render(<IntentGate />);

    await submit("연남동에서 뭘 하면 좋을까");
    expect(await screen.findByText("어떤 업종을 생각하세요?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "잘 몰라요 — 동네부터 볼게요" }));

    expect(router.push).toHaveBeenCalledWith("/map?region=1144071000");
    expect(api.diagnoseIntent).not.toHaveBeenCalled();
  });

  it("동도 구도 없으면 25구 칩 → 그 구의 동 칩 2단으로 되묻는다", async () => {
    api.parseIntent.mockResolvedValue(result({ intent_type: "C", industry_id: "karaoke", missing: ["region", "budget"] }));
    api.fetchRegionList.mockResolvedValue([
      { region_code: "1168064000", name: "역삼1동" },
      { region_code: "1168065000", name: "역삼2동" },
      { region_code: "1144071000", name: "연남동" },
    ]);
    api.diagnoseIntent.mockResolvedValue(result({ intent_type: "A", region_code: "1168065000", industry_id: "karaoke", diagnosis: null }));
    render(<IntentGate />);

    await submit("노래방 하고 싶어요");
    expect(await screen.findByText(/말씀하신 곳을 찾지 못했어요/)).toBeInTheDocument();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "강남구" })); });

    expect(await screen.findByText("강남구의 어느 동인가요?")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "연남동" })).toBeNull(); // 다른 구의 동은 안 나온다
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "역삼2동" })); });

    // 진단이 없으면 문장 없이 바로 착지한다 — 진단 실패가 착지를 막지 않는다
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/map?region=1168065000&industry=karaoke"));
  });

  it("동을 모르면 우회로로 C유형 착지 — 업종만 싣는다", async () => {
    api.parseIntent.mockResolvedValue(result({ intent_type: "C", industry_id: "gym", missing: ["region", "budget"] }));
    render(<IntentGate />);

    await submit("헬스장");
    await screen.findByText(/말씀하신 곳을 찾지 못했어요/);
    fireEvent.click(screen.getByRole("button", { name: "아직 몰라요 — 지도에서 고를게요" }));

    expect(router.push).toHaveBeenCalledWith("/map?industry=gym");
  });

  it("요청이 실패하면 알림을 띄우고 이동하지 않는다", async () => {
    api.parseIntent.mockRejectedValue(new Error("boom"));
    render(<IntentGate />);

    await submit("아무 말");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("예시 칩을 누르면 입력창이 채워진다", () => {
    render(<IntentGate />);
    fireEvent.click(screen.getByRole("button", { name: "홍대 근처 미용실" }));
    expect(screen.getByLabelText("어느 동네에서 무엇을 하려고 하세요?")).toHaveValue("홍대 근처 미용실");
  });
});
