import { expect, it } from "vitest";
import { redirectErrorMessage } from "./auth-errors";

it("구글 왕복 실패 코드는 사람이 읽는 안내로 바꾼다", () => {
  expect(redirectErrorMessage("EMAIL_TAKEN")).toContain("아이디와 비밀번호로 로그인");
  expect(redirectErrorMessage("OAUTH_STATE_MISMATCH")).toContain("만료");
});

it("모르는 코드는 일반 안내, 코드가 없으면 null", () => {
  expect(redirectErrorMessage("SOMETHING_NEW")).toBe("로그인하지 못했습니다. 다시 시도해 주세요.");
  expect(redirectErrorMessage(null)).toBeNull();
});
