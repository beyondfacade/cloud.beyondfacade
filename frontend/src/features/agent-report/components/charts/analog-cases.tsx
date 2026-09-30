import type { CategoryOutlook, EventAnalogs, EventImpact, IndustryMove, UnavailableFact, WindowImpact } from "@/shared/api/types";
import { availableFact } from "../../lib/available-fact";

const REASON_LABEL: Record<EventAnalogs["categories"][number]["reason"], string> = {
  question: "질문 속 상황",
  current: "진행 중 이벤트",
};

function formatPp(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%p`;
}

/** 강세·약세·내 업종을 한 줄로 모아 변동폭 순으로 — 같은 업종이 두 번 나오지 않게. */
function windowRows(window: WindowImpact): { move: IndustryMove & { excess_pct: number }; mine: boolean }[] {
  const byId = new Map<string, IndustryMove>();
  for (const move of [...window.strongest, ...window.weakest, ...(window.target ? [window.target] : [])]) byId.set(move.industry_id, move);
  return [...byId.values()]
    .filter((move): move is IndustryMove & { excess_pct: number } => move.excess_pct !== null)
    .sort((a, b) => b.excess_pct - a.excess_pct)
    .map((move) => ({ move, mine: move.industry_id === window.target?.industry_id }));
}

function WindowBars({ window }: { window: WindowImpact }) {
  const rows = windowRows(window);
  const max = Math.max(0.1, ...rows.map(({ move }) => Math.abs(move.excess_pct)));
  const title = `${window.label} ${window.start_month}~${window.end_month}`;
  return (
    <div role="group" aria-label={title} className="flex flex-col gap-2">
      <p className="text-xs text-[var(--text-secondary)]">{window.label} <span className="tabular-nums">{window.start_month}~{window.end_month}</span></p>
      {rows.length === 0 ? <p className="text-sm text-[var(--text-secondary)]">자료 없음</p> : (
        <ul className="flex flex-col gap-1.5">
          {rows.map(({ move, mine }) => {
            const width = (Math.abs(move.excess_pct) / max) * 50;
            const positive = move.excess_pct >= 0;
            return (
              <li key={move.industry_id} aria-label={`${move.industry_name} ${formatPp(move.excess_pct)}${mine ? " (내 업종)" : ""}`}
                className="grid grid-cols-[5.5rem_1fr_3.5rem] items-center gap-2 text-xs">
                <span className={mine ? "font-semibold text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}>{move.industry_name}</span>
                <span className="relative h-2 rounded bg-[var(--bg-raised)]">
                  <span aria-hidden className="absolute inset-y-[-2px] left-1/2 border-l border-[var(--border)]" />
                  <span data-testid="bar" className="absolute inset-y-0 rounded"
                    style={{ left: positive ? "50%" : `${50 - width}%`, width: `${width}%`, backgroundColor: positive ? "var(--ok)" : "var(--danger)" }} />
                </span>
                <span className={`text-right tabular-nums ${mine ? "font-semibold text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}>{formatPp(move.excess_pct)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

const TREND_LABEL: Record<CategoryOutlook["target_trend"], string> = {
  weak: "내 업종은 평소보다 약했어요",
  strong: "내 업종은 평소보다 강했어요",
  mixed: "내 업종은 뚜렷한 방향이 없었어요",
  unknown: "내 업종은 판단할 자료가 없어요",
};

function IndustryChips({ label, industries, color }: { label: string; industries: CategoryOutlook["recommended"]; color: string }) {
  if (industries.length === 0) return null;
  return (
    <ul aria-label={label} className="flex flex-wrap items-center gap-1.5 text-xs">
      <li className="text-[var(--text-secondary)]">{label}</li>
      {industries.map((i) => (
        <li key={i.industry_id} className="rounded-full border px-2 py-0.5" style={{ borderColor: color, color }}>{i.industry_name}</li>
      ))}
    </ul>
  );
}

function OutlookCard({ outlook }: { outlook: CategoryOutlook }) {
  const duration = outlook.typical_duration_months !== null ? ` · 보통 약 ${outlook.typical_duration_months}개월 이어짐` : "";
  return (
    <article aria-label={`${outlook.label} 사례 종합`} className="flex flex-col gap-2 rounded-lg bg-[var(--bg-raised)] p-3">
      <p className="text-sm text-[var(--text-primary)]">
        <span className="font-medium">{outlook.label}</span> 사례 {outlook.analog_count}건 — {TREND_LABEL[outlook.target_trend]}
        <span className="text-xs text-[var(--text-secondary)]">{duration}</span>
      </p>
      <IndustryChips label="거듭 강세" industries={outlook.recommended} color="var(--ok)" />
      <IndustryChips label="거듭 약세" industries={outlook.avoid} color="var(--danger)" />
    </article>
  );
}

function EventCard({ event }: { event: EventImpact }) {
  const period = `${event.start_date} ~ ${event.end_date ?? "진행 중"}${event.duration_months !== null ? ` · 약 ${event.duration_months}개월` : ""}`;
  return (
    <article aria-label={event.name} className="flex flex-col gap-3 border-t border-[var(--border)] pt-4">
      <header className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-[var(--text-primary)]">{event.name}</span>
        {event.current && <span className="rounded-full border border-[var(--accent)] px-2 py-0.5 text-xs text-[var(--accent)]">진행 중</span>}
        <span className="rounded-full bg-[var(--bg-raised)] px-2 py-0.5 text-xs text-[var(--text-secondary)]">{event.category_label}</span>
        <span className="ml-auto text-xs tabular-nums text-[var(--text-secondary)]">{period}</span>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {event.windows.map((window) => <WindowBars key={window.kind} window={window} />)}
      </div>
    </article>
  );
}

export function AnalogCases({ analogs }: { analogs?: EventAnalogs | UnavailableFact }) {
  const data = availableFact(analogs);
  if (!data) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  const events = [...data.current_events, ...data.analogs];
  return (
    <section aria-label="유사 사례 변동폭" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">비슷한 일이 있었을 때 업종 변동폭</h3>
        <p className="text-xs text-[var(--text-secondary)]">서울 전체 점포수 증감, 전년 같은 달 대비 %p · 기준 {data.as_of}</p>
      </div>
      {data.categories.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {data.categories.map((c) => (
            <li key={c.category} className="rounded-full bg-[var(--bg-raised)] px-2.5 py-0.5 text-xs text-[var(--text-secondary)]">{c.label} · {REASON_LABEL[c.reason]}</li>
          ))}
        </ul>
      )}
      {(data.outlooks ?? []).map((outlook) => <OutlookCard key={outlook.category} outlook={outlook} />)}
      {events.length === 0 ? <p className="text-sm text-[var(--text-secondary)]">비교할 이벤트가 없습니다.</p>
        : events.map((event) => <EventCard key={event.event_id} event={event} />)}
      {data.caveats.length > 0 && (
        <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
          {data.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}
        </ul>
      )}
    </section>
  );
}
