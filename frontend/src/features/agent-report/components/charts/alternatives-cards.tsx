import type { ReportFacts, VerdictCode } from "@/shared/api/types";
import { verdictLabel } from "@/shared/verdict";
import { availableFact } from "../../lib/available-fact";

const BADGE_TOKEN: Record<VerdictCode, string> = {
  red: "var(--danger)",
  orange: "var(--warn)",
  clear: "var(--text-secondary)",
  insufficient: "var(--border)",
};

export function AlternativesCards({ alternatives }: { alternatives?: ReportFacts["alternatives"] }) {
  const data = availableFact(alternatives);
  if (!data) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  const axes = [
    { label: "굳이 이 동네라면", items: (data.industries ?? []).map((item) => ({ id: item.industry_id, name: item.industry_name, code: item.verdict_code })) },
    { label: "굳이 이 업종이라면", items: (data.regions ?? []).map((item) => ({ id: item.region_code, name: item.region_name, code: item.verdict_code })) },
  ];
  return <div className="grid gap-4 sm:grid-cols-2">
    {axes.map((axis) => <section key={axis.label} aria-label={axis.label}>
      <h3 className="mb-2 text-sm font-semibold text-[var(--text-primary)]">{axis.label}</h3>
      {axis.items.length ? <ul className="space-y-2">
        {axis.items.slice(0, 3).map((item) => <li key={item.id} className="flex items-center justify-between gap-2 rounded-lg border border-[var(--border)] p-3 text-sm">
          <span>{item.name}</span><span className="shrink-0 rounded border px-2 py-0.5 text-xs" style={{ color: BADGE_TOKEN[item.code], borderColor: BADGE_TOKEN[item.code] }}>{verdictLabel(item.code).name}</span>
        </li>)}
      </ul> : <p className="text-sm text-[var(--text-secondary)]">대안 없음</p>}
    </section>)}
  </div>;
}
