import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MapView } from "./map-view";

const mapConstructor = vi.hoisted(() => vi.fn());
const mapData = vi.hoisted(() => ({ rowsError: false, geojsonData: undefined as unknown, refetchRows: vi.fn(), refetchGeojson: vi.fn() }));
const probeLoseContext = vi.fn();
vi.mock("maplibre-gl", () => ({ Map: function MockMap(options: unknown) { return mapConstructor(options); }, setWorkerUrl: vi.fn() }));
vi.mock("../hooks/use-map-data", () => ({
  useMapData: () => ({
    geojson: { isError: false, data: mapData.geojsonData, refetch: mapData.refetchGeojson }, rows: { isError: mapData.rowsError, isSuccess: !mapData.rowsError, data: [], refetch: mapData.refetchRows }, source: { kind: "categorical", axis: "region_quarter", palette: () => ({}), order: [] },
  }),
}));
vi.mock("./map-legend", () => ({ MapLegend: () => null }));
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

function renderMap() {
  return render(<MapView metric="neighborhood_type" industry="cafe" year={2026} yearQuarter="20211" regionCode="1168064000" onSelectRegion={vi.fn()} showClosed={false} />);
}

beforeEach(() => {
  mapConstructor.mockReset();
  mapData.rowsError = false;
  mapData.geojsonData = undefined;
  mapData.refetchRows.mockReset();
  mapData.refetchGeojson.mockReset();
  probeLoseContext.mockReset();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => ({
    getExtension: () => ({ loseContext: probeLoseContext }),
  }) as never);
});
afterEach(() => vi.restoreAllMocks());

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

  it("경계 소스 실패를 타일과 구별하고 재시도한다", () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    const geojson = { type: "FeatureCollection", features: [] };
    mapData.geojsonData = geojson;
    renderMap();
    map.emit("load", {});
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

  it("API 실패는 지도 오류와 구분해 표시하고 다시 조회할 수 있다", () => {
    const map = fakeMap();
    mapConstructor.mockImplementation(() => map);
    mapData.rowsError = true;
    renderMap();
    expect(screen.getByRole("alert")).toHaveTextContent("지도 데이터를 불러오지 못했습니다");
    fireEvent.click(screen.getByRole("button", { name: "데이터 다시 시도" }));
    expect(mapData.refetchRows).toHaveBeenCalledTimes(1);
  });

  it("선택 분기 지도에 자료가 없으면 연도 대신 분기를 말한다", () => {
    mapConstructor.mockImplementation(() => fakeMap());
    renderMap();
    expect(screen.getByRole("status")).toHaveTextContent("해당 분기의 지표 데이터가 없습니다");
  });
});
