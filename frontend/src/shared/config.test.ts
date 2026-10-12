import { describe, expect, it } from "vitest";
import { config } from "./config";

describe("config", () => {
  it("apiBase 기본값은 /api/mock", () => {
    expect(config.apiBase).toBe("/api/mock");
  });

  it("행정동 경계 경로는 같은 사이트의 정적 GeoJSON 파일이다", () => {
    expect(config.regionsGeoJsonPath).toBe("/geojson/seoul-regions.geojson");
  });
});
