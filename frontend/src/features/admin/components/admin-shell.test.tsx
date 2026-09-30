import { screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import * as api from "../api";
import { AdminShell } from "./admin-shell";
import { renderWithQuery } from "./test-utils";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/admin/security" }));

afterEach(() => vi.restoreAllMocks());

it("좌측 상단 로고를 누르면 서비스 메인 페이지로 간다", () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "viewer", role: "viewer", can_operate: false });
  renderWithQuery(<AdminShell>본문</AdminShell>);
  expect(screen.getByRole("link", { name: "Metabole 첫 화면" })).toHaveAttribute("href", "/");
});
