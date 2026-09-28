import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { MapPage } from "./map-page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("industry=cafe&metric=neighborhood_type&year=2026&year_quarter=20211&region=1168064000"),
}));
vi.mock("./map-view", () => ({ MapView: () => null }));
vi.mock("./control-bar", () => ({ ControlBar: () => null }));
vi.mock("./side-panel", () => ({ SidePanel: () => null }));

it("동을 선택하면 지도 머리말에 상점 위치가 현재 자료임을 밝힌다", () => {
  render(<MapPage />);
  expect(screen.getByText("상점 위치 · 현재 자료")).toBeInTheDocument();
});
