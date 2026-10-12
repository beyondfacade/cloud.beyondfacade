import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { AdminMe, ChatExpert, ChatMessage, ChatRoom } from "@/shared/api/types";
import { openExpertChat, rememberExpertIndustry } from "@/shared/lib/open-expert-chat";
import { GlobalChat } from "./global-chat";

const navigation = vi.hoisted(() => ({ pathname: "/map" }));
vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname }));

class FakeEventSource {
  static CLOSED = 2;
  static last: FakeEventSource | null = null;
  readyState = 1;
  onerror: (() => void) | null = null;
  listeners = new Map<string, (event: MessageEvent<string>) => void>();
  constructor(public url: string) {
    FakeEventSource.last = this;
  }
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(type, listener);
  }
  emit(type: string, payload: unknown) {
    this.listeners.get(type)?.({ data: JSON.stringify(payload) } as MessageEvent<string>);
  }
  close() {}
}

const OPS: AdminMe = { username: "ops", role: "operator", can_operate: true };
const VIEWER: AdminMe = { username: "viewer", role: "viewer", can_operate: false };
const message = (id: number, over: Partial<ChatMessage> = {}): ChatMessage => ({
  id, room: "global", sender_id: 2, sender_username: "viewer", sender_role: "viewer", body: `메시지 ${id}`,
  deleted: false, created_at: new Date().toISOString(), reply_to: null, attachment: null, ...over,
});
const room = (key: string, over: Partial<ChatRoom> = {}): ChatRoom => ({
  key, kind: key.startsWith("dm:") ? "direct" : (key as ChatRoom["kind"]), title: key === "global" ? "전체" : key,
  partner_id: null, unread: 0, last_message: null, ...over,
});
const json = (status: number, body: unknown) => new Response(status === 204 ? null : JSON.stringify(body), { status });

let fetchMock: ReturnType<typeof vi.fn>;

const EXPERTS: ChatExpert[] = [
  { id: 5, username: "park.expert", specialty: "카페", hourly_rate: 30_000, status: "available", avatar_version: null },
  { id: 6, username: "choi.expert", specialty: "부동산", hourly_rate: 20_000, status: "busy", avatar_version: 4 },
];

function setup(me: AdminMe | null, rooms: ChatRoom[] = [room("global")], items: ChatMessage[] = [message(1)], experts = EXPERTS) {
  fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.endsWith("/admin/auth/me")) {
      return Promise.resolve(me ? json(200, me) : json(401, { error: { code: "UNAUTHENTICATED", message: "로그인이 필요합니다." } }));
    }
    if (url.endsWith("/chat/rooms")) return Promise.resolve(json(200, rooms));
    if (url.endsWith("/attachment")) return Promise.resolve(new Response("%PDF-1.4", { headers: { "content-type": "application/pdf" } }));
    if (url.includes("/attachments?name=")) {
      return Promise.resolve(json(201, message(100, { room: "dm:2:5", body: "계획서.pdf", attachment: { name: "계획서.pdf", size: 8 } })));
    }
    if (url.includes("/messages") && method === "GET") return Promise.resolve(json(200, { items, has_more: false }));
    if (url.includes("/messages") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      return Promise.resolve(json(201, message(99, { sender_username: me!.username, body: body.body })));
    }
    if (url.endsWith("/chat/members")) return Promise.resolve(json(200, experts));
    if (url.endsWith("/chat/consultations")) return Promise.resolve(json(201, room("dm:2:5", { title: "park.expert", partner_id: 5 })));
    if (url.endsWith("/chat/direct")) return Promise.resolve(json(200, room("dm:2:5", { title: "park.expert", partner_id: 5 })));
    if (url.includes("/chat/reads/")) return Promise.resolve(json(200, { room: "global", last_read_id: 1 }));
    if (method === "DELETE") return Promise.resolve(json(204, null));
    return Promise.resolve(json(404, { error: { code: "NOT_FOUND", message: "없음" } }));
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("EventSource", FakeEventSource);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><GlobalChat /></QueryClientProvider>);
}

const calls = (fragment: string, method = "GET") =>
  fetchMock.mock.calls.filter(([url, init]) => String(url).includes(fragment) && (init?.method ?? "GET") === method);

beforeEach(() => {
  navigation.pathname = "/map";
  sessionStorage.clear();
  FakeEventSource.last = null;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("비로그인도 채팅 버튼은 보이고, 열면 지금 화면으로 돌아오는 로그인·가입 안내를 본다", async () => {
  setup(null);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  expect(screen.getByText("로그인한 회원만 참여할 수 있어요")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "로그인" })).toHaveAttribute("href", "/login?next=%2Fmap");
  expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute("href", "/signup?next=%2Fmap");
  expect(FakeEventSource.last).toBeNull();
  expect(calls("/chat/rooms")).toHaveLength(0);
});

it("전문가와 연결하기 이벤트가 오면 창이 열리고 DM의 전문가 목록(전문 업종 포함)을 보여 준다", async () => {
  setup(VIEWER);
  await screen.findByRole("button", { name: "채팅 열기" });
  act(() => openExpertChat());
  const list = await screen.findByRole("list", { name: "전문가 목록" });
  expect(within(list).getByText("카페 전문")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "DM" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("combobox", { name: "DM 보기" })).toHaveValue("experts");
  expect(calls("/chat/direct", "POST")).toHaveLength(0);
});

it("전문가 목록 기본 순서는 무작위로 섞인다", async () => {
  vi.spyOn(Math, "random").mockReturnValue(0); // 섞기 결과 = 응답(park → choi)의 역순
  setup(VIEWER);
  await screen.findByRole("button", { name: "채팅 열기" });
  act(() => openExpertChat());
  const text = (await screen.findByRole("list", { name: "전문가 목록" })).textContent ?? "";
  expect(text.indexOf("choi.expert")).toBeLessThan(text.indexOf("park.expert"));
  vi.mocked(Math.random).mockRestore();
});

it("전문가가 올린 사진이 있으면 그 사진, 없으면 이력서 더미 사진을 쓴다", async () => {
  setup(VIEWER);
  await screen.findByRole("button", { name: "채팅 열기" });
  act(() => openExpertChat());
  const list = await screen.findByRole("list", { name: "전문가 목록" });
  const photos = [...list.querySelectorAll("img")].map((img) => img.getAttribute("src"));
  expect(photos).toEqual(expect.arrayContaining(["/api/mock/admin/auth/avatars/6?v=4", "/experts/expert-6.jpg"]));
});

it("리포트로 고른 업종이 있으면 그 업종 전문가가 전문가 목록 맨 위에 온다", async () => {
  vi.spyOn(Math, "random").mockReturnValue(0.99); // 섞어도 응답 순서(park → choi) 그대로
  rememberExpertIndustry("부동산중개업");
  setup(VIEWER);
  await screen.findByRole("button", { name: "채팅 열기" });
  act(() => openExpertChat());
  const list = await screen.findByRole("list", { name: "전문가 목록" });
  const text = list.textContent ?? "";
  expect(text.indexOf("choi.expert")).toBeLessThan(text.indexOf("park.expert"));
  vi.mocked(Math.random).mockRestore();
});

it("대화한 전문가가 없으면 DM을 누를 때 전문가 목록이 열리고, 드롭다운으로 오가며 상담을 사면 그 방이 열린다", async () => {
  setup(VIEWER);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  await userEvent.click(screen.getByRole("tab", { name: "DM" }));
  const view = await screen.findByRole("combobox", { name: "DM 보기" });
  expect([...view.querySelectorAll("option")].map((o) => o.textContent)).toEqual(["전문가 목록", "대화한 전문가"]);
  expect(view).toHaveValue("experts");
  await userEvent.selectOptions(view, "rooms");
  expect(screen.getByText(/아직 대화한 전문가가 없어요/)).toBeInTheDocument();
  await userEvent.selectOptions(view, "experts");
  const list = await screen.findByRole("list", { name: "전문가 목록" });
  expect(within(list).getByText("시간당 30,000원", { exact: false })).toBeInTheDocument();
  expect(within(list).getByRole("button", { name: "대화 중" })).toBeDisabled();
  await userEvent.selectOptions(within(list).getByRole("combobox", { name: "park.expert 상담 시간" }), "2");
  await userEvent.click(within(list).getByRole("button", { name: "구매" }));
  await waitFor(() => expect(calls("/chat/consultations", "POST")).toHaveLength(1));
  expect(JSON.parse(String(calls("/chat/consultations", "POST")[0][1].body))).toEqual({ expert_id: 5, hours: 2 });
  expect(await screen.findByRole("button", { name: "대화 목록으로" })).toBeInTheDocument();
});

it("DM을 누를 때 대화한 방이 있어도 지금 시간을 산 전문가가 있어야 대화한 전문가가 열린다", async () => {
  const rooms = [room("global"), room("dm:2:5", { title: "park.expert", partner_id: 5, unread: 1, last_message: message(3, { room: "dm:2:5" }) })];
  setup(VIEWER, rooms, [message(1)], [{ ...EXPERTS[0], status: "mine" }, EXPERTS[1]]);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  await userEvent.click(await screen.findByRole("tab", { name: /^DM\s*1$/ }));
  expect(await screen.findByRole("combobox", { name: "DM 보기" })).toHaveValue("rooms");
  expect(screen.getByRole("button", { name: /park\.expert/ })).toBeInTheDocument();
});

it("대화한 방만 있고 지금 산 시간이 없으면 DM을 누를 때 전문가 목록이 열린다", async () => {
  const rooms = [room("global"), room("dm:2:5", { title: "park.expert", partner_id: 5, unread: 1, last_message: message(3, { room: "dm:2:5" }) })];
  setup(VIEWER, rooms);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  await userEvent.click(await screen.findByRole("tab", { name: /^DM\s*1$/ }));
  expect(await screen.findByRole("combobox", { name: "DM 보기" })).toHaveValue("experts");
  expect(await screen.findByRole("list", { name: "전문가 목록" })).toBeInTheDocument();
});

it("전문가는 1:1을 먼저 걸 수 없어 DM에 드롭다운 없이 받은 대화만 본다", async () => {
  setup({ username: "park.expert", role: "expert", can_operate: false });
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  await userEvent.click(screen.getByRole("tab", { name: "DM" }));
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(screen.getByText(/일반 회원이 전문가에게 걸면 생겨요/)).toBeInTheDocument();
});

it("로그인·가입 화면에서는 채팅 버튼을 띄우지 않는다", async () => {
  navigation.pathname = "/login";
  setup(OPS);
  await waitFor(() => expect(calls("/admin/auth/me")).toHaveLength(1));
  expect(screen.queryByRole("button", { name: "채팅 열기" })).not.toBeInTheDocument();
});

it("안 읽은 메시지 합계를 버튼 배지로 보여 주고 99를 넘으면 99+", async () => {
  setup(VIEWER, [room("global", { unread: 120 }), room("dm:1:2", { unread: 3, title: "ops" })]);
  expect(await screen.findByLabelText("안 읽은 메시지 123개")).toHaveTextContent("99+");
});

it("글로벌 채팅/DM 토글이 있고, 일반 회원에게는 글로벌 채팅방 드롭다운이 없다", async () => {
  setup(VIEWER);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["글로벌 채팅", "DM"]);
  expect(screen.queryByRole("combobox", { name: "글로벌 채팅방" })).not.toBeInTheDocument();
  expect(await screen.findByText("메시지 1")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "PDF 첨부" })).not.toBeInTheDocument(); // PDF는 1:1에서만
});

it("1:1 대화에서 PDF를 올리고, 첨부 카드를 누르면 PDF를 크게 본다", async () => {
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: () => "blob:pdf", revokeObjectURL: () => {} }));
  sessionStorage.setItem("metabole-chat-v2", JSON.stringify({
    open: true, mode: "direct", room: "global", directView: "rooms", dm: { key: "dm:2:5", title: "park.expert", owner: "viewer" },
  }));
  const shared = message(7, { room: "dm:2:5", sender_username: "park.expert", body: "자료.pdf", attachment: { name: "자료.pdf", size: 2048 } });
  setup(VIEWER, [room("global")], [shared]);
  await userEvent.upload(await screen.findByLabelText("PDF 파일"), new File(["%PDF-1.4"], "계획서.pdf", { type: "application/pdf" }));
  await waitFor(() => expect(calls("/attachments", "POST")).toHaveLength(1));
  expect(String(calls("/attachments", "POST")[0][0])).toContain(`name=${encodeURIComponent("계획서.pdf")}`);
  expect(await screen.findByRole("button", { name: "계획서.pdf PDF 크게 보기" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "자료.pdf PDF 크게 보기" }));
  const viewer = await screen.findByRole("dialog", { name: "자료.pdf 보기" });
  expect(await within(viewer).findByTitle("자료.pdf")).toHaveAttribute("src", "blob:pdf");
  expect(calls("/chat/messages/7/attachment")).toHaveLength(1);
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: "자료.pdf 보기" })).not.toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "메타볼레 채팅" })).toBeInTheDocument(); // 채팅 창은 그대로
});

it("관리자는 글로벌 채팅 드롭다운으로 전체·관리자 방을 고르고, 남의 메시지에 삭제 버튼이 있다", async () => {
  vi.stubGlobal("confirm", () => true);
  setup(OPS, [room("global"), room("operators", { unread: 2 })]);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  const select = screen.getByRole("combobox", { name: "글로벌 채팅방" });
  expect([...select.querySelectorAll("option")].map((o) => o.textContent)).toEqual(["전체", "관리자 (2)"]);
  await userEvent.selectOptions(select, "operators");
  await waitFor(() => expect(calls("/chat/rooms/operators/messages")).toHaveLength(1));
  await userEvent.selectOptions(select, "global");
  await screen.findByText("메시지 1");
  await userEvent.click(screen.getByRole("button", { name: "삭제" }));
  await waitFor(() => expect(calls("/chat/messages/1", "DELETE")).toHaveLength(1));
  expect(await screen.findByText("삭제된 메시지입니다")).toBeInTheDocument();
});

it("Enter로 보내고, 한글 조합 중 Enter와 Shift+Enter는 보내지 않는다", async () => {
  setup(VIEWER);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  const input = await screen.findByRole("textbox", { name: "메시지 입력" });
  await userEvent.type(input, "안녕하세요");
  fireEvent.keyDown(input, { key: "Enter", isComposing: true });
  fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
  expect(calls("/messages", "POST")).toHaveLength(0);
  fireEvent.keyDown(input, { key: "Enter" });
  await waitFor(() => expect(calls("/messages", "POST")).toHaveLength(1));
  expect(JSON.parse(String(calls("/messages", "POST")[0][1].body))).toEqual({ body: "안녕하세요", reply_to_id: null });
  expect(await screen.findByText("안녕하세요")).toBeInTheDocument();
  expect(input).toHaveValue("");
});

it("답장을 누르면 인용 막대가 뜨고 보낼 때 원문 id를 함께 보낸다", async () => {
  setup(OPS);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  await screen.findByText("메시지 1");
  await userEvent.click(screen.getByRole("button", { name: "답장" }));
  expect(screen.getByRole("button", { name: "답장 취소" })).toBeInTheDocument();
  expect(screen.getByText(/에게 답장 · 메시지 1/)).toBeInTheDocument();
  await userEvent.type(screen.getByRole("textbox", { name: "메시지 입력" }), "네 반가워요");
  await userEvent.click(screen.getByRole("button", { name: "보내기" }));
  await waitFor(() => expect(calls("/messages", "POST")).toHaveLength(1));
  expect(JSON.parse(String(calls("/messages", "POST")[0][1].body)).reply_to_id).toBe(1);
  expect(screen.queryByRole("button", { name: "답장 취소" })).not.toBeInTheDocument();
});

it("500자를 넘기면 보내기 버튼이 잠기고 글자 수가 경고색이 된다", async () => {
  setup(VIEWER);
  await userEvent.click(await screen.findByRole("button", { name: "채팅 열기" }));
  const input = await screen.findByRole("textbox", { name: "메시지 입력" });
  fireEvent.change(input, { target: { value: "가".repeat(501) } });
  expect(screen.getByRole("button", { name: "보내기" })).toBeDisabled();
  expect(screen.getByText("501/500")).toHaveAttribute("data-over", "true");
});

it("실시간으로 온 메시지는 열린 방에 바로 붙고, 닫혀 있으면 배지가 늘어난다", async () => {
  setup(OPS);
  const launcher = await screen.findByRole("button", { name: "채팅 열기" });
  await waitFor(() => expect(FakeEventSource.last).not.toBeNull());
  await waitFor(() => expect(calls("/chat/rooms")).toHaveLength(1));
  act(() => FakeEventSource.last!.emit("message", { type: "message", room: "global", message_id: 2, message: message(2) }));
  expect(await screen.findByLabelText("안 읽은 메시지 1개")).toBeInTheDocument();
  await userEvent.click(launcher);
  const list = await screen.findByRole("list", { name: "메시지 목록" });
  await within(list).findByText("메시지 1");
  act(() => FakeEventSource.last!.emit("message", { type: "message", room: "global", message_id: 3, message: message(3) }));
  expect(await within(list).findByText("메시지 3")).toBeInTheDocument();
  await waitFor(() => expect(calls("/chat/reads/global", "PUT").length).toBeGreaterThan(0));
});
