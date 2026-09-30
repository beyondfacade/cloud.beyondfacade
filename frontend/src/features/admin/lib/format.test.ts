import { describe, expect, it } from "vitest";
import {
  BLOCK_TTL_OPTIONS,
  EVENT_WINDOWS,
  TREND_WINDOWS,
  formatAxisTime,
  formatRate,
  rateTone,
  formatBytes,
  formatCount,
  formatDateTime,
  formatMs,
  formatRelative,
  formatUptime,
  percentOf,
  usageTone,
} from "./format";

const NOW = Date.parse("2026-09-29T12:00:00+09:00");

describe("formatBytes", () => {
  it("1024진법으로 단위를 올리고 100 미만만 소수 한 자리", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(64 * 1024 ** 3)).toBe("64.0 GB");
    expect(formatBytes(612 * 1024 ** 3)).toBe("612 GB");
  });
  it("값이 없으면 대시", () => expect(formatBytes(null)).toBe("—"));
});

it("가동 시간은 큰 단위 두 개까지만 보여준다", () => {
  expect(formatUptime(3 * 86_400 + 5 * 3_600 + 59)).toBe("3일 5시간");
  expect(formatUptime(2 * 3_600 + 7 * 60)).toBe("2시간 7분");
  expect(formatUptime(90)).toBe("1분");
  expect(formatUptime(null)).toBe("—");
});

it("상대 시각은 방금·분·시간·일 전, 기록이 없으면 그렇다고 말한다", () => {
  expect(formatRelative("2026-09-29T11:59:40+09:00", NOW)).toBe("방금");
  expect(formatRelative("2026-09-29T11:47:00+09:00", NOW)).toBe("13분 전");
  expect(formatRelative("2026-09-29T04:27:10+09:00", NOW)).toBe("7시간 전");
  expect(formatRelative("2026-09-27T05:10:40+09:00", NOW)).toBe("2일 전");
  expect(formatRelative(null, NOW)).toBe("기록 없음");
});

it("지연은 1초 미만 ms, 이상은 초 한 자리", () => {
  expect(formatMs(142)).toBe("142ms");
  expect(formatMs(16_200)).toBe("16.2s");
  expect(formatMs(null)).toBe("—");
});

it("건수는 천 단위 구분, 날짜는 서울 시간", () => {
  expect(formatCount(1_240_000)).toBe("1,240,000");
  expect(formatDateTime("2026-09-29T02:58:42Z")).toContain("11:58");
});

it("사용률은 80% 주의·90% 위험, 분모가 없으면 계산하지 않는다", () => {
  expect(percentOf(26, 64)).toBe(40.6);
  expect(percentOf(1, 0)).toBeNull();
  expect(usageTone(79.9)).toBe("ok");
  expect(usageTone(80)).toBe("warn");
  expect(usageTone(95)).toBe("danger");
  expect(usageTone(null)).toBe("neutral");
});

it("비율은 한 자리 백분율, 5% 주의·20% 위험", () => {
  expect(formatRate(0.0417)).toBe("4.2%");
  expect(formatRate(null)).toBe("—");
  expect(rateTone(0.049)).toBe("ok");
  expect(rateTone(0.05)).toBe("warn");
  expect(rateTone(0.2)).toBe("danger");
  expect(rateTone(null)).toBe("neutral");
});

it("차트 눈금은 하루 이하면 서울 시:분, 넘으면 월.일", () => {
  expect(formatAxisTime("2026-09-29T03:05:00Z", 24)).toBe("12:05");
  expect(formatAxisTime("2026-09-29T03:05:00Z", 168)).toMatch(/09\.\s?29/);
});

it("검색·추세 기간 선택지는 백엔드 허용 범위 안이다", () => {
  expect(EVENT_WINDOWS.every((w) => w.hours >= 1 && w.hours <= 2_160)).toBe(true);
  expect(TREND_WINDOWS.map((w) => w.hours)).toEqual([1, 6, 24, 168]);
});

it("차단 기간은 백엔드 허용 범위 안이고 무기한은 null", () => {
  const bounded = BLOCK_TTL_OPTIONS.flatMap((o) => (o.minutes === null ? [] : [o.minutes]));
  expect(bounded.every((m) => m >= 1 && m <= 43_200)).toBe(true);
  expect(BLOCK_TTL_OPTIONS.at(-1)).toEqual({ label: "무기한", minutes: null });
});
