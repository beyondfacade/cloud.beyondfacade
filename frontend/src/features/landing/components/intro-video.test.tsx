import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IntroVideo } from "./intro-video";

afterEach(() => {
  cleanup();
  document.body.style.overflow = "";
  vi.restoreAllMocks();
});

it("처음 렌더하면 인트로 영상이 자동 재생·음소거 설정으로 보인다", () => {
  render(<IntroVideo />);
  const video = screen.getByRole("dialog", { name: "메타볼레 인트로 영상" }).querySelector("video");

  expect(video).toHaveAttribute("src", "/landing/intro.mp4");
  expect(video).toHaveProperty("autoplay", true);
  expect(video).toHaveProperty("muted", true);
  expect(video).toHaveAttribute("playsinline");
  expect(video).toHaveAttribute("preload", "auto");
  expect(video).toHaveAttribute("aria-hidden", "true");
  expect(video).not.toHaveAttribute("loop");
  expect(video).not.toHaveAttribute("controls");
  expect(screen.getByRole("button", { name: "건너뛰기" })).not.toHaveFocus();
});

it("키보드로 건너뛰기를 누르면 영상 오버레이가 사라진다", async () => {
  const user = userEvent.setup();
  const { container } = render(<IntroVideo />);

  await user.tab();
  expect(screen.getByRole("button", { name: "건너뛰기" })).toHaveFocus();
  await user.keyboard("{Enter}");

  expect(container).toBeEmptyDOMElement();
});

it.each([
  ["ended", "영상이 끝나면"],
  ["error", "영상 오류가 발생하면"],
])("%s 이벤트로 %s 오버레이가 사라진다", (event) => {
  const { container } = render(<IntroVideo />);

  fireEvent(container.querySelector("video")!, new Event(event));

  expect(container).toBeEmptyDOMElement();
});

it("다시 마운트하면 저장소나 쿠키를 사용하지 않고 인트로가 다시 보인다", async () => {
  const getItem = vi.spyOn(Storage.prototype, "getItem");
  const setItem = vi.spyOn(Storage.prototype, "setItem");
  const getCookie = vi.spyOn(document, "cookie", "get");
  const setCookie = vi.spyOn(document, "cookie", "set");
  const user = userEvent.setup();
  const first = render(<IntroVideo />);
  await user.click(screen.getByRole("button", { name: "건너뛰기" }));
  first.unmount();

  render(<IntroVideo />);

  expect(screen.getByRole("dialog", { name: "메타볼레 인트로 영상" })).toBeInTheDocument();
  expect(getItem).not.toHaveBeenCalled();
  expect(setItem).not.toHaveBeenCalled();
  expect(getCookie).not.toHaveBeenCalled();
  expect(setCookie).not.toHaveBeenCalled();
});

it("열려 있는 동안 본문 스크롤을 잠그고 닫히면 기존 값으로 복구한다", async () => {
  document.body.style.overflow = "auto";
  const user = userEvent.setup();
  render(<IntroVideo />);
  expect(document.body.style.overflow).toBe("hidden");

  await user.click(screen.getByRole("button", { name: "건너뛰기" }));

  expect(document.body.style.overflow).toBe("auto");
});

it("열린 상태에서 언마운트해도 본문 스크롤을 기존 값으로 복구한다", () => {
  document.body.style.overflow = "scroll";
  const { unmount } = render(<IntroVideo />);

  unmount();

  expect(document.body.style.overflow).toBe("scroll");
});
