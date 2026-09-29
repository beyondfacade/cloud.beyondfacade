import type { ReportFacts } from "@/shared/api/types";
import { availableFact } from "../../lib/available-fact";

type Metric = "store_count" | "closure_rate" | "growth_rate";
type History = Exclude<ReportFacts["metrics_history"], { available: false }>;
const SERIES: Record<Metric, { label: string; color: string; format: (value: number) => string }> = {
  store_count: { label: "점포수", color: "var(--accent)", format: (v) => `${v.toLocaleString("ko-KR")}개` },
  closure_rate: { label: "폐업률", color: "var(--danger)", format: (v) => `${(v * 100).toFixed(1)}%` },
  growth_rate: { label: "성장률", color: "var(--ok)", format: (v) => `${(v * 100).toFixed(1)}%` },
};

/** 개수와 비율은 별도 축, 두 비율은 같은 축을 공유한다. 색은 테마 토큰을 그대로 사용한다. */
function TrendPlot({ rows, metrics, label }: { rows: History; metrics: Metric[]; label: string }) {
  const values = rows.flatMap((row) => metrics.map((metric) => row[metric])).filter(Number.isFinite);
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const span = max - min || 1;
  const x = (year: number) => 58 + (year - rows[0].year) / (rows[rows.length - 1].year - rows[0].year || 1) * 360;
  const y = (value: number) => 140 - (value - min) / span * 115;
  const axisFormat = SERIES[metrics[0]].format;
  return <figure className="min-w-0">
    <figcaption className="mb-2 flex gap-4 text-xs">
      {metrics.map((metric) => <span key={metric} style={{ color: SERIES[metric].color }}>{SERIES[metric].label}{metric === "growth_rate" && " (점선)"}</span>)}
    </figcaption>
    <svg viewBox="0 0 440 170" width="100%" role="img" aria-label={label}>
      {[min, ...(max === min ? [] : [max])].map((value) => <g key={value}>
        <text x={52} y={y(value) + 4} textAnchor="end" fontSize={10} fill="var(--text-secondary)">{axisFormat(value)}</text>
        <line x1={58} x2={418} y1={y(value)} y2={y(value)} stroke="var(--border)" />
      </g>)}
      {min < 0 && max > 0 && <line x1={58} x2={418} y1={y(0)} y2={y(0)} stroke="var(--border)" strokeDasharray="3 3" />}
      {metrics.map((metric) => {
        const series = SERIES[metric];
        const valid = rows.filter((row) => Number.isFinite(row[metric]));
        return <g key={metric}>
          <polyline points={valid.map((row) => `${x(row.year)},${y(row[metric])}`).join(" ")} fill="none" stroke={series.color} strokeWidth={2} strokeDasharray={metric === "growth_rate" ? "5 3" : undefined} />
          {valid.map((row) => <circle key={row.year} cx={x(row.year)} cy={y(row[metric])} r={3} fill={series.color}>
            <title>{row.year}년 {series.label}: {series.format(row[metric])}</title>
          </circle>)}
        </g>;
      })}
      {rows.map((row) => <text key={row.year} x={x(row.year)} y={160} textAnchor="middle" fontSize={10} fill="var(--text-secondary)">{row.year}</text>)}
    </svg>
  </figure>;
}

export function MetricTrend({ history }: { history?: ReportFacts["metrics_history"] }) {
  const data = availableFact(history);
  if (!Array.isArray(data)) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  const rows = data.filter((row) => Number.isFinite(row.year)).toSorted((a, b) => a.year - b.year).slice(-8);
  if (rows.length < 2) return <p className="text-sm text-[var(--text-secondary)]">추세 자료 없음</p>;
  return <section className="space-y-3" aria-label="연도별 지표 추세">
    <h3 className="text-sm font-semibold text-[var(--text-primary)]">연도별 지표 추세</h3>
    <TrendPlot rows={rows} metrics={["store_count"]} label="점포수 추세" />
    <TrendPlot rows={rows} metrics={["closure_rate", "growth_rate"]} label="폐업률·성장률 추세" />
  </section>;
}
