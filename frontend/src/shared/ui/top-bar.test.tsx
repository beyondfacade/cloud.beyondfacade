import { render, screen } from "@testing-library/react";
import { TopBar } from "./top-bar";

const navigation = vi.hoisted(() => ({ pathname: "/analysis" }));
vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
}));
vi.mock("./account-menu", () => ({ AccountMenu: () => <div data-testid="account-menu" /> }));

beforeEach(() => { navigation.pathname = "/analysis"; });

it("현재 경로의 탭에 aria-current가 표시된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "리포트" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "경고 지도" })).not.toHaveAttribute("aria-current");
});

it("경고 지도 탭은 전용 지도 경로로 연결된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "경고 지도" })).toHaveAttribute("href", "/map");
});

it("서비스 이름을 통해 첫 화면으로 돌아간다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "Metabole" })).toHaveAttribute("href", "/");
});

it("지도 경로에서 경고 지도 탭이 활성화된다", () => {
  navigation.pathname = "/map";
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "경고 지도" })).toHaveAttribute("aria-current", "page");
});

it("관리자 화면은 자체 헤더를 쓰므로 서비스 헤더를 숨긴다", () => {
  navigation.pathname = "/admin/security";
  render(<TopBar />);
  expect(screen.queryByRole("banner")).not.toBeInTheDocument();
});

it("서비스 헤더 오른쪽에 계정 메뉴가 있다", () => {
  render(<TopBar />);
  expect(screen.getByTestId("account-menu")).toBeInTheDocument();
});

it("로그인·가입 화면은 자체 레이아웃을 쓰므로 서비스 헤더를 숨긴다", () => {
  for (const pathname of ["/login", "/signup"]) {
    navigation.pathname = pathname;
    const { unmount } = render(<TopBar />);
    expect(screen.queryByRole("banner")).not.toBeInTheDocument();
    unmount();
  }
});

it("첫 화면에서는 전용 헤더와 내비게이션이 중복되지 않는다", () => {
  navigation.pathname = "/";
  render(<TopBar />);
  expect(screen.queryByRole("banner")).not.toBeInTheDocument();
});
