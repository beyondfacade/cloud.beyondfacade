import type { ReportFacts, ReportSection } from "@/shared/api/types";
import { VerdictCard } from "@/shared/ui/verdict-card";
import { availableFact } from "../lib/available-fact";
import { SignalBars } from "./charts/signal-bars";
import { MetricTrend } from "./charts/metric-trend";
import { NeighborhoodProfileCard } from "./charts/neighborhood-profile";
import { StayingPower } from "./charts/staying-power";
import { TimeBlockBars } from "./charts/time-block-bars";
import { HourGapChart } from "./charts/hour-gap-chart";
import { AlternativesCards } from "./charts/alternatives-cards";
import { FundingCards } from "./charts/funding-cards";

function ShockList({ shocks }: { shocks?: ReportFacts["shocks"] }) {
  if (!Array.isArray(shocks)) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  return <section aria-label="외부 충격" className="space-y-2">
    <h3 className="text-sm font-semibold text-[var(--text-primary)]">외부 충격</h3>
    {shocks.length === 0 ? <p className="text-sm text-[var(--text-secondary)]">자료 없음</p> : <ul className="space-y-2 text-sm">
      {shocks.map((shock, index) => <li key={shock.event_id ?? shock.id ?? index} className="flex flex-wrap justify-between gap-2 border-b border-[var(--border)] py-2">
        <span>{shock.name || shock.title || "이름 없음"}</span>
        {(shock.period || shock.start) && <span className="text-xs text-[var(--text-secondary)]">{shock.period || shock.start}</span>}
      </li>)}
    </ul>}
  </section>;
}

const VISUALS = {
  verdict: (facts: ReportFacts) => {
    const verdict = availableFact(facts.verdict);
    return <>
      {verdict ? <VerdictCard verdict={verdict} industryLabel={facts.region?.industry_name ?? "업종"} /> : <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>}
      <SignalBars verdict={facts.verdict} />
    </>;
  },
  reasons: (facts: ReportFacts) => <>
    <MetricTrend history={facts.metrics_history} />
    <NeighborhoodProfileCard profile={facts.profile} />
    <StayingPower commerceChange={facts.commerce_change} />
    <ShockList shocks={facts.shocks} />
  </>,
  conditions: (facts: ReportFacts) => <>
    <TimeBlockBars profile={facts.profile} />
    <HourGapChart hourGap={facts.hour_gap} />
  </>,
  alternatives: (facts: ReportFacts) => <AlternativesCards alternatives={facts.alternatives} />,
  funding: (facts: ReportFacts) => <FundingCards candidates={facts.funding_candidates} />,
} satisfies Record<ReportSection, (facts: ReportFacts) => React.ReactNode>;

export function ReportVisuals({ facts, section }: { facts: ReportFacts; section: ReportSection }) {
  return <div className="mb-6 space-y-6">{VISUALS[section](facts)}</div>;
}
