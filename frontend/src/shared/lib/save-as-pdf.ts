/** 브라우저 인쇄 창을 연다 — 사용자가 "PDF로 저장"을 고르면 문서 제목이 기본 파일 이름이 된다. */
export function saveAsPdf(fileName: string) {
  const previous = document.title;
  document.title = fileName;
  window.addEventListener("afterprint", () => { document.title = previous; }, { once: true });
  window.print();
}
