import type {
  AnalogQuarter, CategoryOutlook, ConditionCompare, EventAnalogs, EventImpact, IndustrySeries, RecentNews, UnavailableFact,
} from "@/shared/api/types";
import { availableFact } from "../../lib/available-fact";

const REASON_LABEL: Record<EventAnalogs["categories"][number]["reason"], string> = {
  question: "질문 속 상황",
  current: "진행 중 이벤트",
};

function formatPp(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%p`;
}

// 평소 대비 ±0.3%p 밖만 강세·약세로 칠한다 (백엔드 TREND_BAND와 같다)
const TREND_BAND = 0.3;
const MAX_QUARTERS = 12;
// 이 크기(%p)부터 가장 진하게 — 한 분기만 튀는 값이 나머지를 흐리게 만들지 않도록 상한을 둔다
const FULL_TONE = 2;

const ROLE_LABEL: Record<IndustrySeries["role"], string> = {
  target: "내 업종",
  recommended: "거듭 강세",
  avoid: "거듭 약세",
};

const ROLE_COLOR: Record<IndustrySeries["role"], string> = {
  target: "var(--text-primary)",
  recommended: "var(--ok)",
  avoid: "var(--danger)",
};

function tone(value: number | null): "none" | "weak" | "strong" | "flat" {
  if (value === null) return "none";
  if (value <= -TREND_BAND) return "weak";
  if (value >= TREND_BAND) return "strong";
  return "flat";
}

function cellColor(value: number | null): string {
  const t = tone(value);
  if (t === "none") return "transparent";
  if (t === "flat") return "var(--bg-raised)";
  const strength = Math.round(25 + (Math.min(Math.abs(value as number), FULL_TONE) / FULL_TONE) * 75);
  return `color-mix(in srgb, ${t === "strong" ? "var(--ok)" : "var(--danger)"} ${strength}%, transparent)`;
}

function QuarterGrid({ event }: { event: EventImpact }) {
  const years = [...new Set(event.quarters.map((q) => Math.ceil(q.quarter / 4)))];
  // 4분기 사례도 12분기 사례와 칸 너비가 같도록 표 너비를 분기 수에 비례해 줄인다
  return (
    <table aria-label={`${event.name} 분기별 변동폭`} className="table-fixed border-separate border-spacing-0.5 text-xs"
      style={{ width: `calc(7rem + (100% - 7rem) * ${event.quarters.length} / ${MAX_QUARTERS})` }}>
      <colgroup>
        <col className="w-28" />
        {event.quarters.map((q) => <col key={q.quarter} />)}
      </colgroup>
      <thead>
        <tr>
          <th scope="col" className="sr-only">업종</th>
          {years.map((year) => (
            <th key={year} scope="colgroup" colSpan={event.quarters.filter((q) => Math.ceil(q.quarter / 4) === year).length}
              className="border-b border-[var(--border)] pb-0.5 text-center font-normal text-[var(--text-secondary)]">
              {year}년 차
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {event.series.map((series) => (
          <tr key={`${series.role}-${series.industry_id}`}>
            <th scope="row" className="truncate pr-1 text-left font-normal">
              <span aria-hidden="true" className="mr-1 inline-block h-2 w-2 rounded-full align-middle" style={{ backgroundColor: ROLE_COLOR[series.role] }} />
              <span className={series.role === "target" ? "font-semibold text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}>{series.industry_name}</span>
              <span className="sr-only"> ({ROLE_LABEL[series.role]})</span>
            </th>
            {event.quarters.map((q, index) => {
              const value = series.values[index] ?? null;
              const text = `${q.label} ${value === null ? "자료 없음" : formatPp(value)}`;
              return (
                <td key={q.quarter} title={text} data-tone={tone(value)}
                  className={`h-5 rounded-sm ${value === null ? "border border-dashed border-[var(--border)]" : ""}`}
                  style={{ backgroundColor: cellColor(value) }}>
                  <span className="sr-only">{text}</span>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Overlaps({ quarters }: { quarters: AnalogQuarter[] }) {
  const overlapping = quarters.filter((q) => q.overlaps.length > 0);
  if (overlapping.length === 0) return null;
  return (
    <ul aria-label="겹친 이벤트" className="flex flex-col gap-0.5 text-xs text-[var(--text-secondary)]">
      {overlapping.map((q) => <li key={q.quarter}>{q.label} — {q.overlaps.join(", ")}</li>)}
    </ul>
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

function RecentNewsLine({ recent }: { recent: RecentNews }) {
  if (!recent.checked) return <p className="text-xs text-[var(--text-secondary)]">최근 소식은 확인하지 못했어요</p>;
  const subject = `최근 ${recent.days}일 ${recent.keywords.join("·")} 기사`;
  if (recent.article_count === 0) {
    return <p className="text-xs text-[var(--text-secondary)]">{subject} 없음 — 비슷한 상황이 다시 올 때의 참고예요</p>;
  }
  return (
    <div className="flex flex-col gap-1 text-xs">
      <p className="text-[var(--danger)]">{subject} {recent.article_count}건</p>
      <ul className="flex flex-col gap-0.5 text-[var(--text-secondary)]">
        {recent.headlines.map((h) => (
          <li key={h.url}>
            <a href={h.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">{h.title}</a>
            <span className="tabular-nums"> · {h.published_at}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatPct(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

const DIRECTION: Record<ConditionCompare["direction"], { label: string; color: string }> = {
  weaker: { label: "그때보다 약한 상태", color: "var(--danger)" },
  stronger: { label: "그때보다 강한 상태", color: "var(--ok)" },
  similar: { label: "그때와 비슷한 상태", color: "var(--text-secondary)" },
};

function ConditionLine({ condition }: { condition: ConditionCompare }) {
  const { before, recent } = condition;
  const direction = DIRECTION[condition.direction];
  return (
    <p role="note" aria-label="사례 직전 대비 지금" className="text-xs text-[var(--text-secondary)]">
      <span title={`${before.start_month}~${before.end_month} 대비 ${recent.start_month}~${recent.end_month} · 그 사이 여러 변화가 섞인 비교로 이벤트 효과가 아니에요`}>
        {condition.event_name} 직전 4분기 대비 최근 4분기: 점포 {formatPct(before.growth_pct)} → {formatPct(recent.growth_pct)}
        {" "}(전 업종 대비 {formatPp(before.excess_pct)} → {formatPp(recent.excess_pct)}) · 폐업률 {before.closure_rate_pct.toFixed(1)}% → {recent.closure_rate_pct.toFixed(1)}%
      </span>
      {" — "}<span className="font-medium" style={{ color: direction.color }}>{direction.label}</span>
    </p>
  );
}

function OutlookCard({ outlook, recent }: { outlook: CategoryOutlook; recent?: RecentNews }) {
  const duration = outlook.typical_duration_months !== null ? ` · 보통 약 ${outlook.typical_duration_months}개월 이어짐` : "";
  return (
    <article aria-label={`${outlook.label} 사례 종합`} className="flex flex-col gap-2 rounded-lg bg-[var(--bg-raised)] p-3">
      <p className="text-sm text-[var(--text-primary)]">
        <span className="font-medium">{outlook.label}</span> 사례 {outlook.analog_count}건 — {TREND_LABEL[outlook.target_trend]}
        <span className="text-xs text-[var(--text-secondary)]">{duration}</span>
      </p>
      {outlook.condition && <ConditionLine condition={outlook.condition} />}
      {recent && <RecentNewsLine recent={recent} />}
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
      {event.quarters.length === 0 ? <p className="text-sm text-[var(--text-secondary)]">아직 끝난 분기가 없습니다.</p> : (
        <>
          <p className="text-xs text-[var(--text-secondary)]">
            내 업종 {event.quarters.length}분기 중 약세 {event.target_weak_quarters} · 강세 {event.target_strong_quarters}
            {event.target_weak_streak > 0 && ` · 처음부터 ${event.target_weak_streak}분기 연속 약세`}
            {event.quarters.length < event.years * 4 && ` · 비교 기간 ${event.years * 4}분기 중 ${event.quarters.length}분기 지남`}
          </p>
          <QuarterGrid event={event} />
          <Overlaps quarters={event.quarters} />
        </>
      )}
    </article>
  );
}

function CompareHint({ hints }: { hints: NonNullable<EventAnalogs["hints"]> }) {
  if (hints.length === 0) return null;
  return (
    <p role="note" aria-label="다른 상황 비교 안내" className="text-xs text-[var(--text-secondary)]">
      {hints.map((h) => h.label).join(", ")} 사례는 질문에 {hints.map((h) => `"${h.keyword}"`).join(", ")} 같은 단어를 넣으면 함께 비교합니다.
    </p>
  );
}

function scopeLabel(scope: EventAnalogs["scope"]): string {
  if (scope?.level !== "district") return "서울 전체";
  return `내 업종은 ${scope.name}, 비교 업종은 ${scope.comparison_name}`;
}

export function AnalogCases({ analogs }: { analogs?: EventAnalogs | UnavailableFact }) {
  const data = availableFact(analogs);
  if (!data) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  const events = [...data.current_events, ...data.analogs];
  return (
    <section aria-label="유사 사례 변동폭" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">비슷한 일이 있었을 때 업종 변동폭</h3>
        <p className="text-xs text-[var(--text-secondary)]">{scopeLabel(data.scope)} 점포수 증감, 이벤트 직전 1년의 같은 분기 대비 %p · 칸 색은 분기별 강세·약세, 이름 앞 점은 사례에서 거듭 강세·약세 · 기준 {data.as_of}</p>
      </div>
      {data.categories.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {data.categories.map((c) => (
            <li key={c.category} className="rounded-full bg-[var(--bg-raised)] px-2.5 py-0.5 text-xs text-[var(--text-secondary)]">{c.label} · {REASON_LABEL[c.reason]}</li>
          ))}
        </ul>
      )}
      {(data.outlooks ?? []).map((outlook) => (
        <OutlookCard key={outlook.category} outlook={outlook}
          recent={data.recent_news?.find((r) => r.category === outlook.category)} />
      ))}
      {events.length === 0 ? <p className="text-sm text-[var(--text-secondary)]">비교할 이벤트가 없습니다.</p>
        : events.map((event) => <EventCard key={event.event_id} event={event} />)}
      {data.caveats.length > 0 && (
        <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
          {data.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}
        </ul>
      )}
      <CompareHint hints={data.hints ?? []} />
    </section>
  );
}
