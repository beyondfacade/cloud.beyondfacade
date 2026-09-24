import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PlanProfile } from "@/shared/api/types";
import { ProfileForm } from "./profile-form";

const empty: PlanProfile = {
  business_registered: null,
  planned_opening_date: null,
  funds_needed_by: null,
  guarantee_status: "unknown",
  policy_confirmation_status: "unknown",
};

describe("창업 단계 폼", () => {
  it("아직 묻지 않았으면 어느 쪽도 선택돼 있지 않다 — 기본값을 '아니오'로 두지 않는다", () => {
    render(<ProfileForm profile={empty} onChange={vi.fn()} />);

    for (const label of ["등록했어요", "아직 전이에요", "잘 모르겠어요"]) {
      expect(screen.getByLabelText(label)).not.toBeChecked();
    }
  });

  it("'잘 모르겠어요'는 아니오가 아니라 unknown으로 올라간다", async () => {
    const onChange = vi.fn();
    render(<ProfileForm profile={empty} onChange={onChange} />);

    await userEvent.click(screen.getByLabelText("잘 모르겠어요"));

    expect(onChange).toHaveBeenCalledWith({ business_registered: "unknown" });
  });

  it("보증서와 확인서를 따로 묻는다 — 별개 절차다", () => {
    render(<ProfileForm profile={empty} onChange={vi.fn()} />);

    expect(screen.getByLabelText("보증기관 보증서")).toHaveValue("unknown");
    expect(screen.getByLabelText("정책자금 확인서")).toHaveValue("unknown");
    expect(screen.getByText("보증기관 보증서와 정책자금 확인서는 별개 절차입니다.")).toBeInTheDocument();
  });
});
