import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ControlBar } from "./control-bar";
import { DEFAULT_STATE } from "../lib/map-state";

it("업종 선택기만 표시하고 지표·연도·분기 선택기는 표시하지 않는다", () => {
  render(<ControlBar state={DEFAULT_STATE} onChange={vi.fn()} />);
  expect(screen.getAllByRole("combobox")).toHaveLength(1);
  expect(screen.getByRole("combobox", { name: "업종" })).toBeEnabled();
  expect(screen.queryByText("지표")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByText("이 지표는 업종과 무관합니다")).toBeNull();
});

it("업종을 변경해도 선택한 동과 예산을 보존한다", () => {
  const onChange = vi.fn();
  const state = { industry: "cafe", region: "1168064000", budget: 50_000_000 };
  render(<ControlBar state={state} onChange={onChange} />);
  fireEvent.change(screen.getByRole("combobox", { name: "업종" }), { target: { value: "convenience_store" } });
  expect(onChange).toHaveBeenCalledWith({ industry: "convenience_store", region: "1168064000", budget: 50_000_000 });
});
