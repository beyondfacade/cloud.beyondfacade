import { expect, it } from "vitest";
import type { ChildcareCenter, ConvenienceStore, Store } from "@/shared/api/types";
import { markerStrategyOf } from "./marker-strategies";

const CENTER: ChildcareCenter = {
  center_id: "11110000029",
  name: "가회어린이집",
  type_name: "국공립",
  status_name: "정상",
  lat: 37.58,
  lng: 126.98,
  base_date: "2026-09-17",
  capacity: 39,
  child_count: 25,
  waiting_count: 20,
};

const STORE: Store = {
  store_id: "s1",
  name: "스타벅스 신사세로수길점",
  lat: 37.51,
  lng: 127.02,
  status_name: "영업",
  open_date: "2026-08-20",
};

it("어린이집 업종은 어린이집 마커 전략을 쓰고, 팝업에 유형·정원·현원·가동률·대기를 보여준다", () => {
  const strategy = markerStrategyOf("childcare");
  expect(strategy.queryKey("1111051500", "childcare")).toEqual(["childcare-centers", "1111051500"]);
  const text = strategy.buildPopup(CENTER).textContent;
  expect(text).toContain("가회어린이집");
  expect(text).toContain("국공립 · 정상");
  expect(text).toContain("정원 39 · 현원 25 (64.1%)");
  expect(text).toContain("입소대기 20건");
});

it("어린이집 팝업은 상태·대기 공란을 숨기지 않고 원천 그대로 표시한다", () => {
  const text = markerStrategyOf("childcare").buildPopup({ ...CENTER, status_name: null, waiting_count: null })
    .textContent;
  expect(text).toContain("국공립 · 상태 미상");
  expect(text).toContain("입소대기 미공개");
});

it("그 외 업종은 점포 마커 전략을 쓴다", () => {
  const strategy = markerStrategyOf("cafe");
  expect(strategy.queryKey("1168052100", "cafe")).toEqual(["stores", "1168052100", "cafe"]);
  const text = strategy.buildPopup(STORE).textContent;
  expect(text).toContain("스타벅스 신사세로수길점");
  expect(text).toContain("개업일 2026-08-20");
});

it("편의점 업종은 편의점 마커 전략을 쓰고, 팝업에 지점명·브랜드·도로명주소를 보여준다", () => {
  const strategy = markerStrategyOf("convenience_store");
  expect(strategy.queryKey("1168064000", "convenience_store")).toEqual(["convenience-stores", "1168064000"]);
  const store: ConvenienceStore = {
    store_id: "MA010120220800340808",
    name: "세븐일레븐역삼점",
    branch_name: "타워점",
    brand: "세븐일레븐",
    lat: 37.49,
    lng: 127.04,
    road_address: "서울특별시 강남구 논현로63길 19",
  };
  const text = strategy.buildPopup(store).textContent;
  expect(text).toContain("세븐일레븐역삼점 타워점");
  expect(text).toContain("세븐일레븐");
  expect(text).toContain("서울특별시 강남구 논현로63길 19");
});

it("편의점 팝업은 미확인 브랜드를 기타 브랜드로 표시한다", () => {
  const text = markerStrategyOf("convenience_store").buildPopup({
    store_id: "x",
    name: "스토리웨이편의점",
    branch_name: null,
    brand: null,
    lat: 37.49,
    lng: 127.04,
    road_address: null,
  } as ConvenienceStore).textContent;
  expect(text).toContain("기타 브랜드");
});
