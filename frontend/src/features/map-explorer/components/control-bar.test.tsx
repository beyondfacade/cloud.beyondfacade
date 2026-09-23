import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ControlBar } from "./control-bar";
import { DEFAULT_STATE, type MapState } from "../lib/map-state";

function renderBar(overrides: Partial<MapState> = {}) {
  const onChange = vi.fn();
  const state: MapState = { ...DEFAULT_STATE, ...overrides };
  render(<ControlBar state={state} onChange={onChange} />);
  return { onChange, state };
}

describe("컨트롤바 두 무리", () => {
  it("동네·업종 두 무리를 각각 group으로 그리고 지표 7개를 나눠 담는다", () => {
    renderBar();
    const region = screen.getByRole("group", { name: "동네" });
    const industry = screen.getByRole("group", { name: "업종" });
    expect(region.querySelectorAll("button")).toHaveLength(4);
    expect(industry.querySelectorAll("button")).toHaveLength(3);
    expect(screen.getByRole("button", { name: "심야 체류" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "폐업률" })).toBeInTheDocument();
  });

  it("동네 지표가 선택되면 업종 select는 살아 있되 설명이 붙고, 시간 셀렉터는 분기다", () => {
    renderBar({ metric: "neighborhood_type" });
    const industrySelect = screen.getByRole("combobox", { name: /업종/ });
    expect(industrySelect).not.toBeDisabled(); // 사이드패널·마커가 계속 쓴다
    expect(industrySelect).toHaveAccessibleDescription("이 지표는 업종과 무관합니다");
    expect(screen.getByRole("combobox", { name: /분기/ })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: /연도/ })).toBeNull();
    expect(screen.getByRole("option", { name: "2026년 2분기" })).toBeInTheDocument();
  });

  it("업종 지표가 선택되면 설명이 없고 시간 셀렉터는 연도다", () => {
    renderBar({ metric: "closure_rate" });
    expect(screen.queryByText("이 지표는 업종과 무관합니다")).toBeNull();
    expect(screen.getByRole("combobox", { name: /연도/ })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: /분기/ })).toBeNull();
  });

  it("분기를 고르면 year_quarter가 바뀌고, 최신을 고르면 null로 돌아간다", () => {
    const { onChange, state } = renderBar({ metric: "night_index" });
    const quarter = screen.getByRole("combobox", { name: /분기/ });
    fireEvent.change(quarter, { target: { value: "20254" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...state, year_quarter: "20254" });
    fireEvent.change(quarter, { target: { value: "20262" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...state, year_quarter: null });
  });

  it("무리를 바꾸는 클릭은 지표만 바꾸고 연도·분기·예산은 그대로 둔다", () => {
    const { onChange, state } = renderBar({ metric: "night_index", year: 2023, year_quarter: "20244", budget: 50_000_000 });
    fireEvent.click(screen.getByRole("button", { name: "폐업률" }));
    expect(onChange).toHaveBeenLastCalledWith({ ...state, metric: "closure_rate" });
  });
});
