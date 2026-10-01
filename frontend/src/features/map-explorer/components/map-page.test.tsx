import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { MapPage } from "./map-page";

const navigation = vi.hoisted(() => ({ replace: vi.fn(), query: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navigation.replace }),
  useSearchParams: () => new URLSearchParams(navigation.query),
}));
vi.mock("./map-view", () => ({ MapView: () => null }));
vi.mock("./side-panel", () => ({ SidePanel: () => null }));

beforeEach(() => {
  navigation.replace.mockReset();
  navigation.query = "region=1168064000&industry=cafe&budget=50000000";
});

it("동을 선택하면 지도 머리말에 상점 위치가 현재 자료임을 밝힌다", () => {
  render(<MapPage />);
  expect(screen.getByText("상점 위치 · 현재 자료")).toBeInTheDocument();
});

it.each(["", "&metric=closure_rate&year=2021&year_quarter=20211", "&metric=unknown&year=bad&year_quarter=bad"])(
  "관문 URL에 옛 파라미터 %s가 있어도 리다이렉트 없이 업종을 선택한다",
  (legacy) => {
    navigation.query += legacy;
    render(<MapPage />);
    expect(screen.getByRole("combobox", { name: "업종" })).toHaveValue("cafe");
    expect(navigation.replace).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("combobox", { name: "업종" }), { target: { value: "karaoke" } });
    expect(navigation.replace).toHaveBeenCalledWith("?industry=karaoke&region=1168064000&budget=50000000", { scroll: false });
  },
);

it("머리말 제목은 피해야 할 동네부터 보인다고 알린다", () => {
  render(<MapPage />);
  expect(screen.getByRole("heading", { level: 1, name: "피해야 할 동네부터 보입니다." })).toBeInTheDocument();
});

it("지도 머리말 이름표와 지도 영역 이름이 창업 경고 지도를 가리킨다", () => {
  render(<MapPage />);
  expect(screen.getByText("SEOUL WARNING MAP")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "서울 창업 경고 지도" })).toBeInTheDocument();
});
