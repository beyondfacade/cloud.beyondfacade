import type { FinanceResult } from "@/shared/api/types";
import { formatManwon, formatPercent } from "../lib/money";

/** 네 갈래 결과. 헤드라인은 "자기자본 외 조달 필요"다 — 희망대출은 아직 빌리지 않은 돈이라
 *  부족액이 0원이어도 상담 주제는 남는다. "충분합니다" 류 문구를 쓰지 않는다. */
export function ResultFigures({ result }: { result: FinanceResult }) {
  const figures = [
    { label: "총 준비자금", value: result.total_required_funds, hint: `초기 투자 ${formatManwon(result.capex)} + 운영준비금 ${result.reserve_months}개월 ${formatManwon(result.operating_reserve)}` },
    { label: "희망대출 반영 후 남는 부족액", value: result.funding_gap, hint: "희망대출이 전액 승인된다는 가정 — 아직 확보된 돈이 아닙니다" },
    { label: "손익분기 월매출", value: result.bep_revenue, hint: `월 고정비 ${formatManwon(result.monthly_fixed)}` },
  ];
  return (
    <section className="flex flex-col gap-5" aria-label="계산 결과">
      <div className="rounded-xl border border-[var(--accent)] bg-[var(--bg-surface)] p-5">
        <p className="text-xs font-medium text-[var(--text-secondary)]">자기자본 외 조달 필요</p>
        <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums text-[var(--text-primary)]" data-headline>{formatManwon(result.external_funding_need)}</p>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">상담에서 조달 경로(보증·대출·정책자금)를 나눠 물어볼 금액입니다.</p>
      </div>
      <ul className="grid gap-3 sm:grid-cols-3">
        {figures.map((f) => (
          <li key={f.label} className="rounded-lg border border-[var(--border)] p-4">
            <p className="text-xs text-[var(--text-secondary)]">{f.label}</p>
            <p className="mt-1 text-lg font-medium tabular-nums text-[var(--text-primary)]">{formatManwon(f.value)}</p>
            <p className="mt-1 text-[11px] leading-snug text-[var(--text-secondary)]">{f.hint}</p>
          </li>
        ))}
      </ul>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" aria-label="매출 시나리오">
          <thead className="text-xs text-[var(--text-secondary)]"><tr><th className="py-1 text-left font-medium">시나리오</th><th className="text-right font-medium">월매출</th><th className="text-right font-medium">영업이익</th><th className="text-right font-medium">회수</th><th className="text-right font-medium">버티는 기간</th></tr></thead>
          <tbody className="tabular-nums">
            {result.scenarios.map((s) => (
              <tr key={s.name} className="border-t border-[var(--border)]">
                <td className="py-2">{s.name}</td>
                <td className="text-right">{formatManwon(s.monthly_revenue)}</td>
                <td className={`text-right ${s.operating_profit < 0 ? "text-[var(--danger)]" : ""}`}>{formatManwon(s.operating_profit)}</td>
                <td className="text-right">{s.payback_months == null ? "회수 불가" : `${s.payback_months}개월`}</td>
                <td className="text-right">{s.runway_months == null ? "—" : `${s.runway_months}개월`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="text-xs text-[var(--text-secondary)]" aria-label="금리 스트레스">
        {result.stress.map((s) => (
          <li key={s.rate_delta}>금리 +{formatPercent(s.rate_delta)}p → 월 고정비 {formatManwon(s.monthly_fixed)}, 기준 시나리오 영업이익 {formatManwon(s.base_operating_profit)}</li>
        ))}
      </ul>
    </section>
  );
}
