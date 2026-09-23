import { render, screen } from "@testing-library/react";
import { TopBar } from "./top-bar";

const navigation = vi.hoisted(() => ({ pathname: "/analysis" }));
vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
}));

beforeEach(() => { navigation.pathname = "/analysis"; });

it("현재 경로의 탭에 aria-current가 표시된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "AI 분석" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "지도 탐색" })).not.toHaveAttribute("aria-current");
});

it("지도 탐색 탭은 전용 지도 경로로 연결된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "지도 탐색" })).toHaveAttribute("href", "/map");
});

it("서비스 이름을 통해 첫 화면으로 돌아간다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "Metabole" })).toHaveAttribute("href", "/");
});

it("지도 경로에서 지도 탐색 탭이 활성화된다", () => {
  navigation.pathname = "/map";
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "지도 탐색" })).toHaveAttribute("aria-current", "page");
});

it("첫 화면에서는 전용 헤더와 내비게이션이 중복되지 않는다", () => {
  navigation.pathname = "/";
  render(<TopBar />);
  expect(screen.queryByRole("banner")).not.toBeInTheDocument();
});
