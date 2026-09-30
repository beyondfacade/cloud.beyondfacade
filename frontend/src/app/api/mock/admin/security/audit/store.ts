import type { AdminMe, AuditAction, AuditEntry } from "@/shared/api/types";

/** mock 감사 로그 — 개발 서버 프로세스 동안만 유지. 계정·수집기 mock 조치가 여기에 덧붙인다. */
export const auditEntries: AuditEntry[] = [
  { id: 3, occurred_at: "2026-09-29T11:40:12+09:00", action: "probe.run", actor: "ops", target: "llm", detail: "성공 · 1830ms", ip: "10.0.0.5" },
  { id: 2, occurred_at: "2026-09-29T11:32:00+09:00", action: "ip_block.create", actor: "ops", target: "198.51.100.7", detail: "스캐너 경로 탐색 · 1440분", ip: "10.0.0.5" },
  { id: 1, occurred_at: "2026-09-28T18:05:31+09:00", action: "user.suspend", actor: "ops", target: "kim.analyst", detail: "", ip: "10.0.0.5" },
];

export function recordAudit(actor: AdminMe, action: AuditAction, target: string, detail = ""): void {
  const id = Math.max(0, ...auditEntries.map((entry) => entry.id ?? 0)) + 1;
  auditEntries.unshift({ id, occurred_at: new Date().toISOString(), action, actor: actor.username, target, detail, ip: "127.0.0.1" });
}
