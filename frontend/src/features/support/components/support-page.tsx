"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type { RateReference, SupportItem } from "@/shared/api/types";
import { industryLabel } from "@/shared/industries";
import { fetchSupportGuide, fetchSupportRegion } from "../api";
import { SUPPORT_CHANNELS, formatPeriod, formatRate, rateLabel } from "../lib/support-content";

const LINK_CLASS = "text-sm font-medium text-[var(--text-primary)] underline decoration-[var(--border)] underline-offset-2 hover:decoration-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

/** /support — 리포트 하단에서 넘어오는 창업 지원·대출 정보. 동·업종·예산은 되돌아갈 주소에 그대로 싣는다. */
export function SupportPage() {
  const searchParams = useSearchParams();
  const region = searchParams.get("region");
  const industry = searchParams.get("industry");
  const budget = searchParams.get("budget");
  const query = new URLSearchParams(Object.entries({ region, industry, budget }).filter((entry): entry is [string, string] => !!entry[1])).toString();

  const guide = useQuery({
    queryKey: ["support-guide", region, industry],
    queryFn: () => fetchSupportGuide(region, industry),
  });
  const regionInfo = useQuery({
    queryKey: ["support-region", region, industry],
    queryFn: () => fetchSupportRegion(region!, industry!),
    enabled: !!region && !!industry,
    staleTime: 5 * 60 * 1000,
  });
  const districtName = guide.data?.district_name ?? null;

  return (
    <main aria-label="창업 지원·대출 정보" className="mx-auto flex max-w-4xl flex-col gap-10 px-4 py-10">
      <header className="flex flex-col gap-3">
        <Link href={`/analysis${query ? `?${query}` : ""}`} className="w-fit text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">← 리포트로</Link>
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">창업 지원·대출 정보</h1>
          {region && industry && (
            <p className="flex gap-1.5 text-sm text-[var(--text-secondary)]">
              <span>{regionInfo.data?.name ?? "선택한 동네"}</span><span aria-hidden="true">·</span><span>{industryLabel(industry)}</span>
            </p>
          )}
        </div>
        <p className="text-sm text-[var(--text-secondary)]">대출·보증부터 우리 구와 업종에 맞는 지원사업, 상담 창구까지 한곳에 모았어요.</p>
        <p className="rounded-md border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-2 text-xs text-[var(--text-secondary)]">
          자격 확정이 아니라 <strong className="font-medium text-[var(--text-primary)]">해당 가능성이 있는 공고</strong>입니다. 신청 자격·한도·기간은 원문에서 확인하세요.
        </p>
      </header>

      {guide.isPending && <div role="status" aria-label="지원 정보를 불러오는 중" className="h-32 animate-pulse rounded-lg bg-[var(--bg-raised)] motion-reduce:animate-none" />}
      {guide.isError && <p role="alert" className="text-sm text-[var(--danger)]">지원 공고를 불러오지 못했습니다. 아래 상담 창구에서 직접 확인해 보세요.</p>}

      {guide.data && <>
        <GuideSection title="대출·보증" description="정책자금 융자와 보증 공고예요. 아래 금리는 공고의 융자 금리를 견줘 볼 기준으로 보세요.">
          <RateList rates={guide.data.rates} />
          <ProgramList items={guide.data.loans} districtName={districtName} empty="지금 모집 중인 대출·보증 공고를 찾지 못했습니다." />
        </GuideSection>
        {districtName && (
          <GuideSection title={`${districtName} 전용 지원`} description="이 구에 사업장을 둔 사람만 신청할 수 있는 공고예요. 다른 구 전용 공고는 뺐습니다.">
            <ProgramList items={guide.data.district} districtName={districtName} empty={`지금 ${districtName} 전용으로 모집 중인 공고는 없습니다.`} />
          </GuideSection>
        )}
        <GuideSection title="창업·경영 지원" description="교육·컨설팅·시설 개선 같은 지원이에요. 업종 낱말이 들어간 공고를 앞에 두었습니다.">
          <ProgramList items={guide.data.others} districtName={districtName} empty="지금 모집 중인 창업·경영 지원 공고를 찾지 못했습니다." />
        </GuideSection>
      </>}

      <GuideSection title="상담·신청 창구" description="공고가 없을 때도 상시로 상담하거나 신청할 수 있는 공식 창구예요.">
        <ul className="grid gap-3 sm:grid-cols-2">
          {SUPPORT_CHANNELS.map((channel) => (
            <li key={channel.url} className="rounded-lg border border-[var(--border)] p-3">
              <a href={channel.url} target="_blank" rel="noreferrer" className={LINK_CLASS}>{channel.name}</a>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">{channel.description}</p>
            </li>
          ))}
        </ul>
      </GuideSection>

      {region && industry && (
        <section aria-label="자금 계획" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4">
          <p className="text-sm text-[var(--text-secondary)]">얼마를 빌려야 할지 먼저 알아 두면 상담이 빨라져요.</p>
          <Link href={`/plan?${query}`} className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">
            필요한 자금 계산하기 →
          </Link>
        </section>
      )}
    </main>
  );
}

function GuideSection({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">{title}</h2>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">{description}</p>
      </div>
      {children}
    </section>
  );
}

function RateList({ rates }: { rates: RateReference[] }) {
  if (rates.length === 0) return null;
  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      {rates.map((rate) => (
        <div key={rate.rate_type} className="rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-3">
          <dt className="text-xs text-[var(--text-secondary)]">{rateLabel(rate.rate_type)}</dt>
          <dd className="mt-1 flex items-baseline gap-2">
            <span className="text-lg font-semibold text-[var(--text-primary)]">{formatRate(rate.rate_pct)}</span>
            <span className="text-xs text-[var(--text-secondary)]">{formatPeriod(rate.period)} · 한국은행</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ProgramList({ items, districtName, empty }: { items: SupportItem[]; districtName: string | null; empty: string }) {
  if (items.length === 0) return <p className="text-sm text-[var(--text-secondary)]">{empty}</p>;
  return (
    <>
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <li key={item.program_id} className="rounded-lg border border-[var(--border)] p-3">
            {/^https?:\/\//i.test(item.url)
              ? <a href={item.url} target="_blank" rel="noreferrer" className={LINK_CLASS}>{item.title}</a>
              : <span className="text-sm font-medium text-[var(--text-primary)]">{item.title}</span>}
            <p className="mt-1 text-xs text-[var(--text-secondary)]">{item.org} · {item.apply_period || "상시"}</p>
            <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--text-secondary)]">
              <span>{item.why}</span>
              {item.district_match && districtName && <Badge>{districtName} 전용</Badge>}
              {item.industry_match && <Badge>업종 관련</Badge>}
            </p>
          </li>
        ))}
      </ul>
      <p className="text-xs text-[var(--text-secondary)]">출처: 기업마당(중소벤처기업부)</p>
    </>
  );
}

function Badge({ children }: { children: ReactNode }) {
  return <span className="rounded border border-[var(--accent)] px-1.5 py-0.5 text-[var(--accent)]">{children}</span>;
}
