import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FundingCandidate } from "@/shared/api/types";
import { CandidateCards } from "./candidate-cards";

const candidate: FundingCandidate = {
  program_id: "p1", source: "bizinfo", title: "2026년 소상공인 정책자금 융자사업",
  org: "중소벤처기업부", url: "https://example.test/1", apply_period: "상시",
  exec_org: null, field_category: "금융", field_subcategory: null, target_text: "소상공인",
  hashtags: null, apply_begin: null, deadline: null, summary: null, is_expired: false,
  why: "전국 · 소상공인 · 금융",
};

describe("후보 공고 카드", () => {
  it("자격 확정이 아니라는 고지를 목록 위에 둔다", () => {
    render(<CandidateCards candidates={[candidate]} need={31_600_000} />);

    expect(screen.getByText(/자격 확정이 아니라/)).toBeInTheDocument();
    expect(screen.getByText(/해당 가능성이 있는 공고/)).toBeInTheDocument();
  });

  it("조달 필요 금액을 기준으로 찾았다고 밝힌다", () => {
    render(<CandidateCards candidates={[candidate]} need={31_600_000} />);

    expect(screen.getByText(/3,160만 원 기준으로 찾았습니다/)).toBeInTheDocument();
  });

  it("원문 링크를 새 탭으로 열고 걸린 규칙을 보인다", () => {
    render(<CandidateCards candidates={[candidate]} need={null} />);

    const link = screen.getByRole("link", { name: candidate.title });
    expect(link).toHaveAttribute("href", "https://example.test/1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
    expect(screen.getByText("전국 · 소상공인 · 금융")).toBeInTheDocument();
  });

  it("후보가 없으면 없다고 말한다 — 빈 목록을 감추지 않는다", () => {
    render(<CandidateCards candidates={[]} need={null} />);

    expect(screen.getByText("지금 해당하는 공고를 찾지 못했습니다.")).toBeInTheDocument();
  });
});
