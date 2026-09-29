import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { VerdictCard } from "./verdict-card";

it("훅 없이 판정 배지와 산출일을 표시한다", () => {
  render(<VerdictCard industryLabel="카페" verdict={{ region_code: "1", industry_id: "cafe", basis: "permit", verdict_code: "clear", strong_count: 0, on_count: 0, signals: [], computed_at: "2026-09-29T04:30:00+09:00" }} />);
  expect(screen.getByRole("status", { name: "카페 판정: 경고 없음" })).toBeInTheDocument();
  expect(screen.getByText("2026-09-29", { selector: "time" }).parentElement).toHaveTextContent("산출일 2026-09-29");
});
