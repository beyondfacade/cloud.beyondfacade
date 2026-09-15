import { render, screen } from "@testing-library/react";
import { TopBar } from "./top-bar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
}));

it("현재 경로의 탭에 aria-current가 표시된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "AI 분석" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "지도 탐색" })).not.toHaveAttribute("aria-current");
});
