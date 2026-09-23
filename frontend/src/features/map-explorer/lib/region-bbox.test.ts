import { expect, it } from "vitest";
import { bboxOfRegion } from "./region-bbox";

const SAMPLE: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { region_code: "1168064000" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [127.0, 37.5],
            [127.1, 37.5],
            [127.1, 37.6],
            [127.0, 37.6],
            [127.0, 37.5],
          ],
        ],
      },
    },
  ],
};

it("region_code에 해당하는 폴리곤 bbox를 반환한다", () => {
  expect(bboxOfRegion(SAMPLE, "1168064000")).toEqual([127.0, 37.5, 127.1, 37.6]);
});

it("없는 region_code면 null", () => {
  expect(bboxOfRegion(SAMPLE, "0000000000")).toBeNull();
});
