import { render, screen } from "@testing-library/react";
import { ConvenienceSummaryList } from "./convenience-summary";

it("편의점 수와 브랜드별 점포 수를 행으로 렌더링하고, 미확인 브랜드는 기타로 표시한다", () => {
  render(
    <ConvenienceSummaryList
      summary={{
        region_code: "1168064000",
        store_count: 149,
        brands: [
          { brand: "GS25", count: 54 },
          { brand: "세븐일레븐", count: 49 },
          { brand: null, count: 3 },
        ],
        source_stdr_ym: "202606",
      }}
    />,
  );
  expect(screen.getByText("149곳")).toBeInTheDocument();
  expect(screen.getByText("GS25")).toBeInTheDocument();
  expect(screen.getByText("54곳")).toBeInTheDocument();
  expect(screen.getByText("기타")).toBeInTheDocument();
  expect(screen.getByText("기준 2026년 6월")).toBeInTheDocument();
});

it("편의점이 없으면 안내 문구만 보여준다", () => {
  render(
    <ConvenienceSummaryList
      summary={{ region_code: "1168064000", store_count: 0, brands: [], source_stdr_ym: null }}
    />,
  );
  expect(screen.getByText("편의점이 없습니다.")).toBeInTheDocument();
});
