import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MapView } from "./map-view";

const mapConstructor = vi.hoisted(() => vi.fn());
const fetchMock = vi.fn();
let rowsError = false;
let geojsonData: unknown;
let verdictRows: { region_code: string; value: string }[] = [];
const probeLoseContext = vi.fn();
vi.mock("maplibre-gl", () => ({ Map: function MockMap(options: unknown) { return mapConstructor(options); }, setWorkerUrl: vi.fn() }));
vi.mock("./region-markers", () => ({ RegionMarkers: () => null }));

function fakeMap() {
  const handlers = new Map<string, (event: unknown) => void>();
  const regionsSource = { setData: vi.fn() };
  return {
    handlers,
    on: vi.fn((name: string, layerOrHandler: unknown, maybeHandler?: (event: unknown) => void) => {
      if (!maybeHandler) handlers.set(name, layerOrHandler as (event: unknown) => void);
    }),
    getCanvas: vi.fn(() => ({ getContext: vi.fn(() => ({})) })),
    regionsSource,
    getSource: vi.fn((id: string) => id === "regions" ? regionsSource : undefined), getLayer: vi.fn(() => false), addSource: vi.fn(), addLayer: vi.fn(),
    setPaintProperty: vi.fn(), setFilter: vi.fn(), fitBounds: vi.fn(), remove: vi.fn(), refreshTiles: vi.fn(),
    emit(name: string, event: unknown) { act(() => handlers.get(name)?.(event)); },
  };
}

function renderMap(industry = "cafe") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MapView industry={industry} regionCode="1168064000" onSelectRegion={vi.fn()} showClosed={false} /></QueryClientProvider>);
}

beforeEach(() => {
  mapConstructor.mockReset();
  rowsError = false;
  geojsonData = { type: "FeatureCollection", features: [] };
  verdictRows = [];
  fetchMock.mockReset().mockImplementation(async (url: string) => {
    if (url.includes("/regions/geojson")) return new Response(JSON.stringify(geojsonData));
    if (url.includes("/verdicts?")) return rowsError
      ? new Response(JSON.stringify({ error: { code: "SERVER_ERROR", message: "조회 실패" } }), { status: 500 })
      : new Response(JSON.stringify(verdictRows));
    throw new Error(`예상하지 않은 요청: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  probeLoseContext.mockReset();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => ({
    getExtension: () => ({ loseContext: probeLoseContext }),
  }) as never);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("지도 실패 상태", () => {
  it("WebGL 초기화가 실패하면 이유와 재시도를 보여준다", () => {
    mapConstructor.mockImplementationOnce(() => { throw new Error("WebGL unavailable"); });
    const map = fakeMap();
    mapConstructor.mockImplementationOnce(() => map);
    renderMap();
    expect(screen.getByRole("alert")).toHaveTextContent("지도를 시작할 수 없습니다");
    fireEvent.click(screen.getByRole("button", { name: "지도 다시 시도" }));
    expect(mapConstructor).toHaveBeenCalledTimes(2);
  });

  it("생성자가 반환했어도 WebGL2 문맥이 없으면 초기화 실패와 재시도를 보여준다", () => {
    const incomplete = fakeMap();
    incomplete.getCanvas.mockReturnValue({ getContext: vi.fn(() => null) });
    mapConstructor.mockImplementationOnce(() => incomplete).mockImplementationOnce(() => fakeMap());
    renderMap();
    expect(screen.getByRole("alert")).toHaveTextContent("지도를 시작할 수 없습니다");
    fireEvent.click(screen.getByRole("button", { name: "지도 다시 시도" }));
    expect(mapConstructor).toHaveBeenCalledTimes(2);
  });

  it("WebGL2가 없는 브라우저에서는 생성자 실행 전에 실패하고, 재시도 때 다시 검사한다", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValueOnce(null as never);
    mapConstructor.mockImplementation(() => fakeMap());
    renderMap();
    expect(screen.getByRole("alert")).toHaveTextContent("지도를 시작할 수 없습니다");
    expect(mapConstructor).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "지도 다시 시도" }));
    expect(mapConstructor).toHaveBeenCalledTimes(1);
    expect(probeLoseContext).toHaveBeenCalledTimes(1);
  });

  it("성공한 WebGL2 사전 검사의 임시 문맥을 해제한다", () => {
    mapConstructor.mockImplementation(() => fakeMap());
    renderMap();
    expect(probeLoseContext).toHaveBeenCalledTimes(1);
  });

  it("타일 오류는 알리고 성공적인 타일 로드 뒤 상태를 지운다", () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    renderMap();
    map.emit("error", { sourceId: "vworld", tile: { tileID: { key: "tile-A" } }, error: new Error("tile HTTP 500") });
    expect(screen.getByRole("alert")).toHaveTextContent("배경 지도 타일");
    expect(screen.getByRole("alert")).not.toHaveTextContent("HTTP 500");
    map.emit("sourcedata", { sourceId: "vworld", tile: { state: "loaded" }, coord: { key: "tile-B" } });
    expect(screen.getByRole("alert")).toHaveTextContent("배경 지도 타일");
    fireEvent.click(screen.getByRole("button", { name: "지도 다시 시도" }));
    expect(map.refreshTiles).toHaveBeenCalledWith("vworld");
    expect(screen.getByRole("alert")).toHaveTextContent("배경 지도 타일");
    map.emit("sourcedata", { sourceId: "vworld", tile: { state: "loaded" }, coord: { key: "tile-A" } });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("여러 실패 타일은 모두 회복되어야 경고를 지운다", () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    renderMap();
    map.emit("error", { sourceId: "vworld", tile: { tileID: { key: "tile-A" } }, error: new Error("tile A") });
    map.emit("error", { sourceId: "vworld", tile: { tileID: { key: "tile-C" } }, error: new Error("tile C") });
    map.emit("sourcedata", { sourceId: "vworld", tile: { state: "loaded" }, coord: { key: "tile-A" } });
    expect(screen.getByRole("alert")).toHaveTextContent("배경 지도 타일");
    map.emit("sourcedata", { sourceId: "vworld", tile: { state: "loaded" }, coord: { key: "tile-C" } });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("화면 밖으로 제거된 실패 타일만 추적에서 빼고 마지막 제거 뒤 경고를 지운다", () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    renderMap();
    map.emit("error", { sourceId: "vworld", tile: { tileID: { key: "tile-A" } }, error: new Error("tile A") });
    map.emit("error", { sourceId: "vworld", tile: { tileID: { key: "tile-B" } }, error: new Error("tile B") });
    map.emit("sourcedataabort", { sourceId: "vworld", tile: { aborted: true, tileID: { key: "tile-X" } }, coord: { key: "tile-X" } });
    expect(screen.getByRole("alert")).toHaveTextContent("배경 지도 타일");
    map.emit("sourcedataabort", { sourceId: "vworld", tile: { aborted: true, tileID: { key: "tile-A" } }, coord: { key: "tile-A" } });
    expect(screen.getByRole("alert")).toHaveTextContent("배경 지도 타일");
    map.emit("sourcedataabort", { sourceId: "vworld", tile: { aborted: true, tileID: { key: "tile-B" } }, coord: { key: "tile-B" } });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("취소된 타일 요청은 영구 오류로 표시하지 않는다", () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    renderMap();
    map.emit("error", { sourceId: "vworld", error: new DOMException("aborted", "AbortError") });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("경계 소스 실패를 타일과 구별하고 재시도한다", async () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    const geojson = { type: "FeatureCollection", features: [] };
    geojsonData = geojson;
    renderMap();
    map.emit("load", {});
    await waitFor(() => expect(map.regionsSource.setData).toHaveBeenCalledWith(geojson));
    map.regionsSource.setData.mockClear();
    map.emit("error", { sourceId: "regions", error: new Error("worker failed") });
    expect(screen.getByRole("alert")).toHaveTextContent("지도 소스");
    fireEvent.click(screen.getByRole("button", { name: "지도 다시 시도" }));
    expect(map.regionsSource.setData).toHaveBeenCalledWith(geojson);
    expect(map.refreshTiles).not.toHaveBeenCalledWith("regions");
    expect(screen.getByRole("alert")).toHaveTextContent("지도 소스");
    map.emit("sourcedata", { sourceId: "regions", sourceDataType: "content" });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("API 실패는 지도 오류와 구분해 표시하고 다시 조회할 수 있다", async () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    rowsError = true;
    renderMap();
    expect(await screen.findByRole("alert")).toHaveTextContent("지도 데이터를 불러오지 못했습니다");
    fireEvent.click(screen.getByRole("button", { name: "데이터 다시 시도" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => url.includes("/verdicts?"))).toHaveLength(2));
  });

  it("판정이 비어 있으면 최신 배치 안내를 표시한다", async () => {
    mapConstructor.mockImplementation(() => fakeMap());
    renderMap();
    expect(await screen.findByRole("status")).toHaveTextContent("이 업종의 판정이 아직 없습니다");
  });
});

it("업종만으로 최신 판정을 조회하고 지도와 범례에 같은 판정 색을 쓴다", async () => {
  const map = fakeMap();
  mapConstructor.mockImplementation(() => map);
  verdictRows = [{ region_code: "1168064000", value: "red" }];
  renderMap("korean_food");
  map.emit("load", {});
  expect(await screen.findByText("비추천")).toBeInTheDocument();
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(expect.arrayContaining([
    "/api/mock/regions/geojson", "/api/mock/verdicts?industry=korean_food",
  ]));
  const swatch = screen.getByText("비추천").closest("li")!.querySelector("span")!;
  const paint = map.setPaintProperty.mock.calls.filter(([, property]) => property === "fill-color").at(-1)![2];
  const color = document.createElement("span");
  color.style.backgroundColor = paint[3];
  expect(color.style.backgroundColor).toBe(swatch.style.backgroundColor);
  expect(paint[2]).toBe("1168064000");
});

it("판정 제외 업종은 조회를 생략하고 준비 중 안내와 무색 지도를 표시한다", async () => {
  const map = fakeMap();
  mapConstructor.mockImplementation(() => map);
  renderMap("convenience_store");
  map.emit("load", {});
  expect(await screen.findByRole("status")).toHaveTextContent("판정 준비 중인 업종");
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/mock/regions/geojson"]);
  expect(screen.queryByText("창업 경고")).toBeNull();
  expect(map.setPaintProperty).toHaveBeenCalledWith("regions-fill", "fill-color", "#cccccc");
});
