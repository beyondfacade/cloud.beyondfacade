import { render, screen } from "@testing-library/react";
import { SiteFooter } from "./site-footer";

const navigation = vi.hoisted(() => ({ pathname: "/analysis" }));
vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname }));

beforeEach(() => { navigation.pathname = "/analysis"; });

it("공통 푸터에서 데이터 출처 전체 페이지로 이동한다", () => {
  render(<SiteFooter />);
  expect(screen.getByRole("link", { name: "데이터 출처 전체 보기 →" })).toHaveAttribute("href", "/sources");
});

it("지도 화면에서는 푸터를 숨겨 화면 높이를 유지한다", () => {
  navigation.pathname = "/map";
  const { container } = render(<SiteFooter />);
  expect(container).toBeEmptyDOMElement();
});
