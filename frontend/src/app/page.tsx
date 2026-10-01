import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { IntentGate } from "@/features/intent-gate/components/intent-gate";
import { LandingPage } from "@/features/landing/components/landing-page";

export const metadata: Metadata = {
  title: "서울 상권 메타볼레 | Metabole",
  description: "가게 자리를 찾기 전에, 피해야 할 자리부터. 서울 427개 동 × 12개 업종의 개업·폐업 기록으로 창업 경고 여부를 판정하고 대안과 필요 자금까지 이어서 확인합니다.",
};

export default async function Home({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  if (["region", "industry", "metric", "year"].some((key) => query[key] !== undefined)) {
    const forwarded = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined) continue;
      for (const item of Array.isArray(value) ? value : [value]) forwarded.append(key, item);
    }
    redirect(`/map?${forwarded.toString()}`);
  }
  // 관문은 랜딩 히어로 슬롯에 들어간다 — 두 feature를 잇는 곳은 여기뿐이다 (§14)
  return <LandingPage hero={<IntentGate />} />;
}
