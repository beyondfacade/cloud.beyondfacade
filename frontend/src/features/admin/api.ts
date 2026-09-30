import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/shared/api/client";
import type {
  AccessEventPage,
  AdminMe,
  AdminRole,
  AdminSessionInfo,
  AdminUser,
  AdminUserCreate,
  AdminUserFilter,
  AuditAction,
  AuditPage,
  CollectorLog,
  CollectorRun,
  FacilitySnapshot,
  HealthcareSnapshot,
  HostHistory,
  IpBlock,
  IpBlockCreate,
  ProbeKind,
  ProbeResult,
  SecurityEventFilter,
  SecurityOverview,
  UsageSeries,
} from "@/shared/api/types";

/** 빈 값은 빼고 쿼리 문자열로 — 서버 기본값을 그대로 쓰게 한다. */
function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

const userPath = (username: string) => `/admin/users/${encodeURIComponent(username)}`;

/** 세션은 httpOnly 쿠키 — 같은 origin 요청이라 fetch가 자동으로 싣는다. 토큰은 JS에 노출되지 않는다. */
export function logoutAdmin(): Promise<void> {
  return apiPost<void>("/admin/auth/logout", {});
}

export function fetchAdminMe(): Promise<AdminMe> {
  return apiGet<AdminMe>("/admin/auth/me");
}

export function changeMyPassword(currentPassword: string, newPassword: string): Promise<void> {
  return apiPost<void>("/admin/auth/password", { current_password: currentPassword, new_password: newPassword });
}

export function fetchSecurityOverview(): Promise<SecurityOverview> {
  return apiGet<SecurityOverview>("/admin/security/overview");
}

export function fetchSecurityEvents(filter: SecurityEventFilter, beforeId: number | null): Promise<AccessEventPage> {
  return apiGet<AccessEventPage>(
    `/admin/security/events${query({ kind: filter.kind, ip: filter.ip.trim(), hours: filter.hours, before_id: beforeId })}`,
  );
}

export function fetchAuditPage(action: AuditAction | null, beforeId: number | null): Promise<AuditPage> {
  return apiGet<AuditPage>(`/admin/security/audit${query({ action, before_id: beforeId })}`);
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

export function fetchUsageSeries(hours: number): Promise<UsageSeries> {
  return apiGet<UsageSeries>(`/admin/healthcare/usage-series${query({ hours })}`);
}

export function runProbe(kind: ProbeKind, message: string): Promise<ProbeResult> {
  return apiPost<ProbeResult>("/admin/healthcare/probe", { kind, message });
}

export function fetchFacilitySnapshot(): Promise<FacilitySnapshot> {
  return apiGet<FacilitySnapshot>("/admin/facility/snapshot");
}

export function fetchHostHistory(hours: number): Promise<HostHistory> {
  return apiGet<HostHistory>(`/admin/facility/history${query({ hours })}`);
}

export function fetchCollectorLog(key: string, lines = 200): Promise<CollectorLog> {
  return apiGet<CollectorLog>(`/admin/facility/collectors/${encodeURIComponent(key)}/log${query({ lines })}`);
}

export function runCollector(key: string): Promise<CollectorRun> {
  return apiPost<CollectorRun>(`/admin/facility/collectors/${encodeURIComponent(key)}/run`, {});
}

export function fetchAdminUsers(filter: AdminUserFilter): Promise<{ items: AdminUser[] }> {
  return apiGet<{ items: AdminUser[] }>(`/admin/users${query({ q: filter.q.trim(), role: filter.role, status: filter.status })}`);
}

export function createAdminUser(body: AdminUserCreate): Promise<AdminUser> {
  return apiPost<AdminUser>("/admin/users", body);
}

export function changeAdminRole(username: string, role: AdminRole): Promise<AdminUser> {
  return apiPatch<AdminUser>(`${userPath(username)}/role`, { role });
}

export function setAdminActive(username: string, active: boolean): Promise<AdminUser> {
  return apiPatch<AdminUser>(`${userPath(username)}/status`, { active });
}

export function resetAdminPassword(username: string, password: string): Promise<void> {
  return apiPut<void>(`${userPath(username)}/password`, { password });
}

export function fetchAdminSessions(username: string): Promise<{ items: AdminSessionInfo[] }> {
  return apiGet<{ items: AdminSessionInfo[] }>(`${userPath(username)}/sessions`);
}

export function revokeAdminSessions(username: string): Promise<{ revoked: number }> {
  return apiDelete<{ revoked: number }>(`${userPath(username)}/sessions`);
}
