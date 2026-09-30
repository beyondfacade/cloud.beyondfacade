import { apiDelete, apiGet, apiPost } from "@/shared/api/client";
import type {
  AdminMe,
  FacilitySnapshot,
  HealthcareSnapshot,
  IpBlock,
  IpBlockCreate,
  ProbeKind,
  ProbeResult,
  SecurityOverview,
} from "@/shared/api/types";

/** 세션은 httpOnly 쿠키 — 같은 origin 요청이라 fetch가 자동으로 싣는다. 토큰은 JS에 노출되지 않는다. */
export function loginAdmin(username: string, password: string): Promise<AdminMe> {
  return apiPost<AdminMe>("/admin/auth/login", { username, password });
}

export function logoutAdmin(): Promise<void> {
  return apiPost<void>("/admin/auth/logout", {});
}

export function fetchAdminMe(): Promise<AdminMe> {
  return apiGet<AdminMe>("/admin/auth/me");
}

export function fetchSecurityOverview(): Promise<SecurityOverview> {
  return apiGet<SecurityOverview>("/admin/security/overview");
}

export function fetchIpBlocks(): Promise<IpBlock[]> {
  return apiGet<IpBlock[]>("/admin/security/ip-blocks");
}

export function createIpBlock(body: IpBlockCreate): Promise<IpBlock> {
  return apiPost<IpBlock>("/admin/security/ip-blocks", body);
}

export function deleteIpBlock(ip: string): Promise<void> {
  return apiDelete(`/admin/security/ip-blocks/${encodeURIComponent(ip)}`);
}

export function fetchHealthcareSnapshot(): Promise<HealthcareSnapshot> {
  return apiGet<HealthcareSnapshot>("/admin/healthcare/snapshot");
}

export function runProbe(kind: ProbeKind, message: string): Promise<ProbeResult> {
  return apiPost<ProbeResult>("/admin/healthcare/probe", { kind, message });
}

export function fetchFacilitySnapshot(): Promise<FacilitySnapshot> {
  return apiGet<FacilitySnapshot>("/admin/facility/snapshot");
}
