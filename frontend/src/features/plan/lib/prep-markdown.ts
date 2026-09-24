import type { FundingCandidate, PlanProfile, PlanQuestion } from "@/shared/api/types";
import { AMOUNT_LABELS, type AmountField } from "./form-defaults";
import { formatManwon, formatPercent } from "./money";
import type { PlanDraft, PlanSnapshot } from "./plan-draft";

/** 상담 준비자료 Markdown. **숫자는 서버 결과를 그대로 쓴다** — 여기서 다시 계산하지 않는다.
 *  은행 전송·예약·신청은 하지 않으므로 확정·승인을 뜻하는 문구를 쓰지 않는다. */

const RATIO_LABELS: Record<string, string> = {
  cost_ratio: "원가율",
  fee_ratio: "수수료율",
  loan_rate: "대출 연금리",
};

const REGISTERED_LABELS: Record<string, string> = {
  true: "등록함",
  false: "등록 전",
  unknown: "모름 — 상담에서 확인",
  null: "확인 안 함",
};

const STATUS_LABELS: Record<string, string> = {
  not_started: "시작 전",
  in_progress: "진행 중",
  issued: "발급 완료",
  unknown: "모름 — 상담에서 확인",
};

const KIND_LABELS: Record<string, string> = {
  gap: "조달",
  assumption: "가정",
  procedure: "절차",
};

export interface PrepContext {
  draft: PlanDraft;
  regionName: string | null;
  industryLabel: string;
  candidates: FundingCandidate[];
  /** 프리필 단서 — 어떤 값이 어디서 왔고 무엇을 조심할지. 전부 싣는다. */
  caveats: string[];
}

function profileLines(profile: PlanProfile): string[] {
  return [
    `- 사업자등록: ${REGISTERED_LABELS[String(profile.business_registered)] ?? "확인 안 함"}`,
    `- 개업 예정일: ${profile.planned_opening_date || "미정"}`,
    `- 자금 필요일: ${profile.funds_needed_by || "미정"}`,
    `- 보증기관 보증서: ${STATUS_LABELS[profile.guarantee_status]}`,
    `- 정책자금 확인서: ${STATUS_LABELS[profile.policy_confirmation_status]}`,
  ];
}

function planTable(plan: PlanSnapshot): string[] {
  const amounts = (Object.keys(AMOUNT_LABELS) as AmountField[]).map(
    (field) => `| ${AMOUNT_LABELS[field]} | ${formatManwon(plan.input[field])} |`,
  );
  const ratios = Object.entries(RATIO_LABELS).map(
    ([key, label]) => `| ${label} | ${formatPercent(plan.input[key as keyof typeof plan.input] as number)} |`,
  );
  return ["| 항목 | 값 |", "|---|---:|", ...amounts, ...ratios];
}

function resultLines(plan: PlanSnapshot): string[] {
  const r = plan.result;
  return [
    `- **자기자본 외 조달 필요: ${formatManwon(r.external_funding_need)}** — 상담에서 조달 경로를 나눠 물어볼 금액입니다.`,
    `- 총 준비자금: ${formatManwon(r.total_required_funds)} (초기 투자 ${formatManwon(r.capex)} + 운영준비금 ${r.reserve_months}개월 ${formatManwon(r.operating_reserve)})`,
    `- 희망대출 반영 후 남는 부족액: ${formatManwon(r.funding_gap)} — 희망대출이 전액 실행된다는 가정입니다.`,
    `- 손익분기 월매출: ${formatManwon(r.bep_revenue)} (월 고정비 ${formatManwon(r.monthly_fixed)})`,
  ];
}

function comparisonLines(draft: PlanDraft): string[] {
  if (!draft.baseline || !draft.current) return [];
  const rows: [string, number, number][] = [
    ["월세", draft.baseline.input.monthly_rent, draft.current.input.monthly_rent],
    ["예상 월매출", draft.baseline.input.expected_monthly_revenue, draft.current.input.expected_monthly_revenue],
    ["총 준비자금", draft.baseline.result.total_required_funds, draft.current.result.total_required_funds],
    ["자기자본 외 조달 필요", draft.baseline.result.external_funding_need, draft.current.result.external_funding_need],
  ];
  return [
    "## 최초안과 현재안",
    "",
    "| 항목 | 최초안 | 현재안 |",
    "|---|---:|---:|",
    ...rows.map(([label, a, b]) => `| ${label} | ${formatManwon(a)} | ${formatManwon(b)} |`),
  ];
}

export function buildPrepMarkdown(ctx: PrepContext): string {
  const { draft } = ctx;
  const plan = draft.selected ? draft[draft.selected] : null;
  if (!plan) return "";

  const where = [ctx.regionName, ctx.industryLabel].filter(Boolean).join(" · ");
  const planName = draft.selected === "baseline" ? "최초안" : "현재안";
  const lines: string[] = [
    "# 창업자금 상담 준비자료",
    "",
    `- 대상: ${where}`,
    `- 상담할 계획: ${planName}`,
    "",
    "> 이 자료는 공개 자료로 계산한 예상치입니다. 자격·한도·금리는 상담에서 확인해야 합니다.",
    "",
    "## 창업 단계",
    "",
    ...profileLines(draft.profile),
    "",
    "## 계산 결과",
    "",
    ...resultLines(plan),
    "",
    "## 입력한 값",
    "",
    ...planTable(plan),
  ];

  if (plan.unconfirmed.length > 0) {
    lines.push(
      "",
      `> 입력하지 않아 0원으로 계산한 항목: ${plan.unconfirmed.map((f) => AMOUNT_LABELS[f]).join(" · ")} — 유효한 0원인지 확인이 필요합니다.`,
    );
  }

  const comparison = comparisonLines(draft);
  if (comparison.length > 0) {
    lines.push("", ...comparison);
    if (draft.change_reason.trim()) lines.push("", `변경 이유: ${draft.change_reason.trim()}`);
  }

  if (ctx.candidates.length > 0) {
    lines.push(
      "",
      "## 찾아본 지원 공고",
      "",
      "> 자격 확정이 아니라 해당 가능성이 있는 공고입니다. 자격·한도는 원문에서 확인하세요.",
      "",
      ...ctx.candidates.map((c) => `- [${c.title}](${c.url}) — ${c.org} · ${c.apply_period} · ${c.why}`),
    );
  }

  if (draft.questions.length > 0) {
    lines.push(
      "",
      "## 상담에서 확인할 것",
      "",
      ...draft.questions.map((q, i) => `${i + 1}. (${KIND_LABELS[q.kind] ?? q.kind}) ${q.text}`),
    );
  }

  if (ctx.caveats.length > 0) {
    lines.push("", "## 값의 출처와 단서", "", ...ctx.caveats.map((c) => `- ${c}`));
  }

  return lines.join("\n") + "\n";
}

/** 질문 목록만 뽑은 짧은 형태 — 화면의 "질문만 복사"용. */
export function buildQuestionsMarkdown(questions: PlanQuestion[]): string {
  if (questions.length === 0) return "";
  return questions.map((q, i) => `${i + 1}. (${KIND_LABELS[q.kind] ?? q.kind}) ${q.text}`).join("\n") + "\n";
}
