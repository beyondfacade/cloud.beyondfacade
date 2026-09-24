import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PlanQuestion } from "@/shared/api/types";
import { QuestionList } from "./question-list";

const questions: PlanQuestion[] = [
  { text: "자기자본 외 3,160만 원을 어떤 경로로 조달할 수 있는지", basis: "조달 필요 > 0", kind: "gap" },
  { text: "보증서 발급 절차와 소요 기간", basis: "보증서 미확인", kind: "procedure" },
];

describe("확인할 질문", () => {
  it("서버가 준 것은 초안이라고 말한다", () => {
    render(<QuestionList questions={questions} onChange={vi.fn()} />);

    expect(screen.getByText(/고치고 지우고 더하세요/)).toBeInTheDocument();
  });

  it("질문을 고치면 그 항목만 바뀐다", async () => {
    const onChange = vi.fn();
    render(<QuestionList questions={questions} onChange={onChange} />);

    await userEvent.type(screen.getByLabelText("질문 1"), "!");

    expect(onChange).toHaveBeenLastCalledWith([
      { ...questions[0], text: `${questions[0].text}!` },
      questions[1],
    ]);
  });

  it("삭제하면 그 항목이 빠진다", async () => {
    const onChange = vi.fn();
    render(<QuestionList questions={questions} onChange={onChange} />);

    await userEvent.click(screen.getByLabelText("질문 1 삭제"));

    expect(onChange).toHaveBeenCalledWith([questions[1]]);
  });

  it("순서를 바꾼다 — 첫 항목은 더 올릴 수 없다", async () => {
    const onChange = vi.fn();
    render(<QuestionList questions={questions} onChange={onChange} />);

    expect(screen.getByLabelText("질문 1 위로")).toBeDisabled();
    await userEvent.click(screen.getByLabelText("질문 1 아래로"));

    expect(onChange).toHaveBeenCalledWith([questions[1], questions[0]]);
  });

  it("직접 쓴 질문을 더한다", async () => {
    const onChange = vi.fn();
    render(<QuestionList questions={questions} onChange={onChange} />);

    await userEvent.type(screen.getByLabelText("질문 추가"), "권리금 회수 가능성{Enter}");

    expect(onChange).toHaveBeenCalledWith([
      ...questions,
      { text: "권리금 회수 가능성", basis: "직접 추가", kind: "procedure" },
    ]);
  });
});
