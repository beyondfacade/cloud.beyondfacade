import type { FinanceResult } from "@/shared/api/types";
import { formatManwon, formatPercent } from "../lib/money";
import { AMOUNT_LABELS, type AmountField } from "../lib/form-defaults";
import styles from "./plan-workspace.module.css";

/** 네 갈래 결과. 헤드라인은 "자기자본 외 조달 필요"다 — 희망대출은 아직 빌리지 않은 돈이라
 *  부족액이 0원이어도 상담 주제는 남는다. "충분합니다" 류 문구를 쓰지 않는다. */
export function ResultFigures({ result, unconfirmed = [] }: { result: FinanceResult; unconfirmed?: AmountField[] }) {
  const figures = [
    { label: "총 준비자금", value: result.total_required_funds, hint: `초기 투자 ${formatManwon(result.capex)} + 운영준비금 ${result.reserve_months}개월 ${formatManwon(result.operating_reserve)}` },
    { label: "희망대출 반영 후 남는 부족액", value: result.funding_gap, hint: "희망대출이 전액 승인된다는 가정 — 아직 확보된 돈이 아닙니다" },
    { label: "손익분기 월매출", value: result.bep_revenue, hint: `월 고정비 ${formatManwon(result.monthly_fixed)}` },
  ];
  return (
    <section className={styles.result} aria-label="계산 결과">
      <div className={styles.headline}>
        <p>자기자본 외 조달 필요</p>
        <p data-headline>{formatManwon(result.external_funding_need)}</p>
        <p className={styles.hint}>직접 준비한 돈 외에 더 마련해야 할 금액이에요.</p>
      </div>
      {unconfirmed.length > 0 && (
        <p className={styles.status} role="status">
          아직 입력하지 않은 {unconfirmed.map((field) => AMOUNT_LABELS[field]).join(" · ")} 항목은 0원으로 계산했어요. 실제 비용을 입력하면 필요한 자금이 달라질 수 있어요.
        </p>
      )}
      <ul className={styles.figures}>
        {figures.map((f) => (
          <li key={f.label}>
            <div><p>{f.label}</p><strong>{formatManwon(f.value)}</strong></div>
            <p className={styles.hint}>{f.hint}</p>
          </li>
        ))}
      </ul>
      <details className={styles.disclosure}>
        <summary>매출이 달라진다면?</summary>
        <div className={styles.scenarios} aria-label="매출 시나리오">
          {result.scenarios.map((s) => (
            <section key={s.name} className={styles.scenario}>
              <h3>{s.name} 시나리오</h3>
              <dl>
                <dt>월매출</dt><dd>{formatManwon(s.monthly_revenue)}</dd>
                <dt>영업이익</dt><dd className={s.operating_profit < 0 ? "text-[var(--danger)]" : undefined}>{formatManwon(s.operating_profit)}</dd>
                <dt>투자금 회수</dt><dd>{s.payback_months == null ? "회수 불가" : `${s.payback_months}개월`}</dd>
                <dt>버티는 기간</dt><dd>{s.runway_months == null ? "—" : `${s.runway_months}개월`}</dd>
              </dl>
            </section>
          ))}
        </div>
      </details>
      <details className={styles.disclosure}>
        <summary>금리가 오른다면?</summary>
        <ul className={`${styles.stress} ${styles.hint}`} aria-label="금리 스트레스">
          {result.stress.map((s) => (
            <li key={s.rate_delta}>금리 +{formatPercent(s.rate_delta)}p → 월 고정비 {formatManwon(s.monthly_fixed)}, 기준 시나리오 영업이익 {formatManwon(s.base_operating_profit)}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}
