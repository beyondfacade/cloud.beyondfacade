import type { AdminUser, FacilitySnapshot, HealthcareSnapshot, SecurityOverview } from "@/shared/api/types";
import type { Tone } from "./format";

export interface DoorStatus {
  tone: Tone;
  label: string;
}

/** 허브 문 배지 — 방마다 이미 쓰는 스냅샷에서 "지금 들어가 봐야 하나"만 뽑는다. */
export function securityStatus(overview: SecurityOverview): DoorStatus {
  const open = overview.summary.open_alerts;
  if (!open) return { tone: "ok", label: "열린 알림 없음" };
  const critical = overview.alerts.some((a) => a.severity === "critical");
  return { tone: critical ? "danger" : "warn", label: `열린 알림 ${open}건` };
}

export function healthcareStatus(snapshot: HealthcareSnapshot): DoorStatus {
  const primary = snapshot.llm_routes.find((r) => r.role === "primary");
  const missing = snapshot.required_models.filter((m) => !m.installed).length;
  if (!snapshot.llm_routes.some((r) => r.available)) return { tone: "danger", label: "LLM 전체 불가" };
  if (!primary?.available) return { tone: "warn", label: "1차 LLM 불가 · 폴백 중" };
  if (missing) return { tone: "warn", label: `필수 모델 ${missing}개 누락` };
  return { tone: "ok", label: "파이프라인 정상" };
}

export function facilityStatus(snapshot: FacilitySnapshot): DoorStatus {
  const down = snapshot.services.filter((s) => !s.ok).length;
  const late = snapshot.collectors.filter((c) => c.status !== "ok").length;
  if (down) return { tone: "danger", label: `서비스 장애 ${down}건${late ? ` · 수집 지연 ${late}건` : ""}` };
  if (late) return { tone: "warn", label: `수집 지연·누락 ${late}건` };
  return { tone: "ok", label: "설비 정상" };
}

export function usersStatus(users: AdminUser[]): DoorStatus {
  const operators = users.filter((u) => u.is_active && u.role === "operator").length;
  const suspended = users.filter((u) => !u.is_active).length;
  if (operators <= 1) return { tone: "warn", label: `활성 운영 관리자 ${operators}명` };
  return { tone: suspended ? "neutral" : "ok", label: `계정 ${users.length}개${suspended ? ` · 정지 ${suspended}` : ""}` };
}
