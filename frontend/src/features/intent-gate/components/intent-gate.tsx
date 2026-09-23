"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import type { IntentResult } from "@/shared/api/types";
import { INDUSTRY_LABELS } from "@/shared/industries";
import { SEOUL_DISTRICTS, districtOf } from "@/shared/seoul-districts";
import { diagnoseIntent, fetchRegionList, parseIntent } from "../api";
import { intentToUrl } from "../lib/intent-url";
import { ClarifyChips, type ChipOption } from "./clarify-chips";
import { DiagnosisLine } from "./diagnosis-line";
import { IntentForm } from "./intent-form";
import styles from "./intent-gate.module.css";

/** 관문 상태 — 한 문장이 A(동+업종)로 완성될 때까지 되묻고, 완성되면 진단을 받아 지도로 보낸다.
 *  후보 칩이 주 경로다: "역삼동"은 역삼1동·2동, "신사동"은 4곳으로 갈라진다. */
type Phase =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "clarifyRegion"; draft: IntentResult; options: ChipOption[]; level: "candidates" | "districts" | "dongs" }
  | { kind: "clarifyIndustry"; draft: IntentResult }
  | { kind: "done"; draft: IntentResult; href: string; sentence: string | null }
  | { kind: "error" };

let regionListCache: Promise<{ region_code: string; name: string }[]> | null = null;
function regionList() {
  regionListCache ??= fetchRegionList();
  return regionListCache;
}

const DISTRICT_OPTIONS: ChipOption[] = Object.entries(SEOUL_DISTRICTS).map(([key, label]) => ({ key, label }));
const INDUSTRY_OPTIONS: ChipOption[] = Object.entries(INDUSTRY_LABELS).map(([key, label]) => ({ key, label }));

export function IntentGate() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const navigate = useCallback((href: string) => router.push(href), [router]);

  /** 동이 정해진 뒤의 갈림길 — 업종이 없으면 되묻고, 있으면 진단을 받아 끝낸다. */
  async function afterRegion(draft: IntentResult) {
    if (!draft.industry_id) {
      setPhase({ kind: "clarifyIndustry", draft });
      return;
    }
    await finish(draft);
  }

  /** A 완성 → 진단이 없으면 두 번째 형태로 한 번 더 묻는다. 진단 실패는 착지를 막지 않는다. */
  async function finish(draft: IntentResult) {
    const href = intentToUrl(draft);
    let sentence = draft.diagnosis?.sentence ?? null;
    if (!sentence && draft.region_code && draft.industry_id) {
      setPhase({ kind: "pending" });
      sentence = await diagnoseIntent(draft.region_code, draft.industry_id)
        .then((r) => r.diagnosis?.sentence ?? null)
        .catch(() => null);
    }
    if (!sentence) {
      navigate(href);
      return;
    }
    setPhase({ kind: "done", draft, href, sentence });
  }

  /** 동이 없을 때 — 후보가 있으면 후보, 구만 잡혔으면 그 구의 동, 아무것도 없으면 25구부터. */
  async function askRegion(draft: IntentResult) {
    if (draft.candidates.length > 0) {
      setPhase({
        kind: "clarifyRegion",
        draft,
        level: "candidates",
        options: draft.candidates.map((c) => ({ key: c.region_code, label: `${c.district_name} ${c.region_name}` })),
      });
      return;
    }
    if (draft.district_code) {
      await askDongs(draft, draft.district_code);
      return;
    }
    setPhase({ kind: "clarifyRegion", draft, level: "districts", options: DISTRICT_OPTIONS });
  }

  async function askDongs(draft: IntentResult, districtCode: string) {
    setPhase({ kind: "pending" });
    const regions = await regionList().catch(() => []);
    const options = regions
      .filter((r) => districtOf(r.region_code) === districtCode)
      .map((r) => ({ key: r.region_code, label: r.name }));
    setPhase({ kind: "clarifyRegion", draft: { ...draft, district_code: districtCode }, level: "dongs", options });
  }

  async function handleSubmit(text: string) {
    setPhase({ kind: "pending" });
    let result: IntentResult;
    try {
      result = await parseIntent(text);
    } catch {
      setPhase({ kind: "error" });
      return;
    }
    if (!result.region_code) await askRegion(result);
    else await afterRegion(result);
  }

  async function handlePickRegion(key: string) {
    if (phase.kind !== "clarifyRegion") return;
    if (phase.level === "districts") {
      await askDongs(phase.draft, key);
      return;
    }
    await afterRegion({ ...phase.draft, region_code: key, candidates: [] });
  }

  function handleSkipRegion() {
    if (phase.kind !== "clarifyRegion") return;
    // C유형 — 동 없이 지도로. T2-1(유형 단계구분도)이 생기면 "이 업종이 잘 되는 동네 유형" 안내로 바뀐다
    navigate(intentToUrl({ ...phase.draft, region_code: null }));
  }

  async function handlePickIndustry(key: string) {
    if (phase.kind !== "clarifyIndustry") return;
    await finish({ ...phase.draft, industry_id: key });
  }

  function handleSkipIndustry() {
    if (phase.kind !== "clarifyIndustry") return;
    // B유형 — 패널이 동네 프로필을 연다
    navigate(intentToUrl({ ...phase.draft, industry_id: null }));
  }

  return (
    <div className={styles.gate}>
      <IntentForm pending={phase.kind === "pending"} onSubmit={handleSubmit} />

      {phase.kind === "error" && (
        <p role="alert" className={styles.error}>요청을 처리하지 못했습니다. 다시 시도해 주세요.</p>
      )}

      {phase.kind === "clarifyRegion" && (
        <ClarifyChips
          prompt={
            phase.level === "candidates"
              ? "어느 동을 말씀하세요? 같은 이름의 동이 여럿이에요."
              : phase.level === "dongs"
                ? `${SEOUL_DISTRICTS[phase.draft.district_code ?? ""] ?? ""}의 어느 동인가요?`
                : "어느 동네를 생각하세요? 말씀하신 곳을 찾지 못했어요."
          }
          options={phase.options}
          onPick={handlePickRegion}
          escape={{ label: "아직 몰라요 — 지도에서 고를게요", onPick: handleSkipRegion }}
        />
      )}

      {phase.kind === "clarifyIndustry" && (
        <ClarifyChips
          prompt="어떤 업종을 생각하세요?"
          options={INDUSTRY_OPTIONS}
          onPick={handlePickIndustry}
          escape={{ label: "잘 몰라요 — 동네부터 볼게요", onPick: handleSkipIndustry }}
        />
      )}

      {phase.kind === "done" && phase.sentence && (
        <DiagnosisLine sentence={phase.sentence} href={phase.href} onNavigate={navigate} />
      )}
    </div>
  );
}
