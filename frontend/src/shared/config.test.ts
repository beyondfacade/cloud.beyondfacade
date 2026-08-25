import { describe, expect, it } from "vitest";
import { config } from "./config";

describe("config", () => {
  it("apiBase 기본값은 /api/mock", () => {
    expect(config.apiBase).toBe("/api/mock");
  });
});
