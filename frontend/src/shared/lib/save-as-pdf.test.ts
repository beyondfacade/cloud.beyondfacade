import { afterEach, expect, it, vi } from "vitest";
import { saveAsPdf } from "./save-as-pdf";

afterEach(() => vi.restoreAllMocks());

it("인쇄 창이 열린 동안 문서 제목을 파일 이름으로 바꾸고 닫히면 되돌린다", () => {
  document.title = "Metabole";
  let titleWhilePrinting = "";
  vi.spyOn(window, "print").mockImplementation(() => { titleWhilePrinting = document.title; });

  saveAsPdf("창업 경고 리포트_역삼1동_카페");
  expect(titleWhilePrinting).toBe("창업 경고 리포트_역삼1동_카페");

  window.dispatchEvent(new Event("afterprint"));
  expect(document.title).toBe("Metabole");
});
