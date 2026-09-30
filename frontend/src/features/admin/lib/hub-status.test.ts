import { expect, it } from "vitest";
import { facilitySnapshotFixture, healthcareSnapshotFixture, securityOverviewFixture } from "@/app/api/mock/admin-fixtures";
import { accounts } from "@/app/api/mock/admin/users/store";
import { facilityStatus, healthcareStatus, securityStatus, usersStatus } from "./hub-status";

it("열린 알림에 심각 등급이 있으면 보안 문은 위험 배지다", () => {
  expect(securityStatus(securityOverviewFixture)).toEqual({ tone: "danger", label: `열린 알림 ${securityOverviewFixture.summary.open_alerts}건` });
  expect(securityStatus({ ...securityOverviewFixture, summary: { ...securityOverviewFixture.summary, open_alerts: 0 } }).tone).toBe("ok");
});

it("1차 LLM이 불가하면 폴백 중, 모두 불가하면 위험이다", () => {
  const routes = healthcareSnapshotFixture.llm_routes;
  const primaryDown = routes.map((r) => (r.role === "primary" ? { ...r, available: false } : { ...r, available: true }));
  expect(healthcareStatus({ ...healthcareSnapshotFixture, llm_routes: primaryDown }).label).toBe("1차 LLM 불가 · 폴백 중");
  const allDown = routes.map((r) => ({ ...r, available: false }));
  expect(healthcareStatus({ ...healthcareSnapshotFixture, llm_routes: allDown }).tone).toBe("danger");
});

it("서비스 장애가 수집 지연보다 우선한다", () => {
  const down = { ...facilitySnapshotFixture, services: facilitySnapshotFixture.services.map((s, i) => ({ ...s, ok: i !== 0 })) };
  expect(facilityStatus(down).tone).toBe("danger");
  const allOk = {
    ...facilitySnapshotFixture,
    services: facilitySnapshotFixture.services.map((s) => ({ ...s, ok: true })),
    collectors: facilitySnapshotFixture.collectors.map((c) => ({ ...c, status: "ok" as const })),
  };
  expect(facilityStatus(allOk)).toEqual({ tone: "ok", label: "설비 정상" });
});

it("활성 관리자가 한 명뿐이면 인사팀 문에 주의를 띄운다", () => {
  const users = [...accounts.values()].map((a) => a.user);
  expect(usersStatus(users).label).toBe("계정 4개 · 정지 1");
  expect(usersStatus(users.filter((u) => u.username !== "lee.ops")).tone).toBe("warn");
});
