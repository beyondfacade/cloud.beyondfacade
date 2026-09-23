import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { LandingPage } from "@/features/landing/components/landing-page";

export const metadata: Metadata = {
  title: "서울 상권 아틀라스 | Metabole",
  description: "서울의 변화 속에서, 내 가게의 자리를 찾다. 지도로 동네의 상권 지표를 살펴보고 AI 분석으로 탐색을 이어가세요.",
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
  return <LandingPage />;
}
