import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AnalysisForm } from "./analysis-form";
import { EXAMPLE_QUESTIONS } from "../lib/example-questions";

function renderForm(industry = "cafe") {
  const onSubmit = vi.fn();
  render(<AnalysisForm initialRegion="1168064000" initialIndustry={industry} onSubmit={onSubmit} />);
  return { onSubmit };
}

it("업종별 예시 질문 칩 3개가 보이고, 첫 문구가 placeholder다", () => {
  renderForm("cafe");
  const list = screen.getByRole("list", { name: "예시 질문" });
  expect(list.querySelectorAll("button")).toHaveLength(3);
  expect(screen.getByRole("textbox", { name: /추가 질문/ })).toHaveAttribute("placeholder", `예: ${EXAMPLE_QUESTIONS.cafe[0]}`);
});

it("칩을 누르면 입력칸이 그 문구로 채워지고 제출에 실린다", () => {
  const { onSubmit } = renderForm("cafe");
  fireEvent.click(screen.getByRole("button", { name: `예시 질문: ${EXAMPLE_QUESTIONS.cafe[1]}` }));
  expect(screen.getByRole("textbox", { name: /추가 질문/ })).toHaveValue(EXAMPLE_QUESTIONS.cafe[1]);
  fireEvent.click(screen.getByRole("button", { name: /분석 시작/ }));
  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({ region: "1168064000", industry: "cafe", question: EXAMPLE_QUESTIONS.cafe[1] }),
  );
});

it("업종을 바꾸면 칩이 바뀌지만 이미 적은 질문은 지우지 않는다", () => {
  renderForm("cafe");
  const textarea = screen.getByRole("textbox", { name: /추가 질문/ });
  fireEvent.change(textarea, { target: { value: "내 질문" } });
  fireEvent.change(screen.getByRole("combobox", { name: /업종/ }), { target: { value: "gym" } });
  expect(screen.getByRole("button", { name: `예시 질문: ${EXAMPLE_QUESTIONS.gym[0]}` })).toBeInTheDocument();
  expect(textarea).toHaveValue("내 질문");
});
