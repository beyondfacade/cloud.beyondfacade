import type { EventAnalogs, UnavailableFact } from "@/shared/api/types";
import { availableFact } from "./available-fact";

/** 근거 표기([확인된 사실]·[참고 신호]) 단위 문단 + 표기 뒤·문장 단위 줄바꿈. LLM이 나눈 줄은 믿지 않고 다시 짠다. */

const GRADE_TAG = /\[(?:확인된 사실|참고 신호)\]/;
const BEFORE_GRADE_TAG = /(?=\[(?:확인된 사실|참고 신호)\])/;
const LEADING_TAG = /^(\[(?:확인된 사실|참고 신호)\])\s*/;
const FACT_TAG = "[확인된 사실]";
const SIGNAL_TAG = "[참고 신호]";
// 한글 뒤 마침표만 문장 끝으로 본다 — "2.9%"·"10,320원" 같은 숫자 안 마침표는 자르지 않는다
const SENTENCE_END = /(?<=[가-힣][.!?])\s+/;
// 사례 속 강세 업종 문장은 과거 값이라 [확인된 사실]이다 — 기준 문장이 없는 저장본에서도 옮긴다
const PAST_FACT = /상대적으로 잘 버/;
// 앞날 전망("…약세일 가능성이 있습니다")은 [참고 신호]다 — 코드 문장이 아닌데 [확인된 사실]에 붙으면 옮긴다
const FORECAST = /가능성이 있습니다[.!?]?$/;
const LEADING_HEADING = /^(#{1,6}\s.*\n+)?([\s\S]*)$/;
// 마크다운 강제 줄바꿈 — 줄 끝 공백 두 칸
const HARD_BREAK = "  \n";
// 이보다 짧은 문장 조각은 기준 문장의 일부로 보지 않는다 (공백 뺀 글자 수)
const MIN_PART_LENGTH = 8;

type Tag = typeof FACT_TAG | typeof SIGNAL_TAG;

/** 리포트 사실의 코드 문장 — LLM이 그대로 옮기므로 본문 문장이 어느 유형·표기인지 가리는 기준이 된다. */
export interface SentenceAnchor {
  category: string;
  tag: Tag;
  text: string;
}

interface Paragraph {
  tag: string;
  sentences: string[];
}

interface Item {
  paragraph: number;
  tag: string;
  text: string;
  category?: string;
}

function parse(paragraph: string): Paragraph {
  const tag = paragraph.match(LEADING_TAG)?.[1] ?? "";
  return { tag, sentences: paragraph.replace(LEADING_TAG, "").split(SENTENCE_END).filter(Boolean) };
}

function movePastFacts(paragraphs: Paragraph[]): Paragraph[] {
  let fact: Paragraph | undefined;
  for (const paragraph of paragraphs) {
    if (paragraph.tag === FACT_TAG) fact = paragraph;
    if (paragraph.tag !== SIGNAL_TAG || !fact) continue;
    fact.sentences.push(...paragraph.sentences.filter((s) => PAST_FACT.test(s)));
    paragraph.sentences = paragraph.sentences.filter((s) => !PAST_FACT.test(s));
  }
  return paragraphs.filter((p) => p.sentences.length > 0);
}

// 비교용 문장 — 공백과 괄호 속 구분어를 뺀다(LLM이 사례 이름 괄호만 바꿔 되풀이한다)
const normalize = (text: string) => text.replace(/\([^)]*\)/g, "").replace(/\s+/g, "");

/** 같은 문장 되풀이는 처음 한 번만 — LLM이 유형 종합·뉴스 문장을 사례마다 다시 붙인다. */
function dropRepeats(paragraphs: Paragraph[]): Paragraph[] {
  const seen = new Set<string>();
  return paragraphs
    .map((p) => ({
      ...p,
      sentences: p.sentences.filter((s) => {
        const key = normalize(s);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }),
    }))
    .filter((p) => p.sentences.length > 0);
}

function matchAnchor(text: string, anchors: SentenceAnchor[], previous?: string): SentenceAnchor | undefined {
  const sentence = normalize(text);
  const candidates = anchors.filter((a) => {
    const anchor = normalize(a.text);
    return sentence.includes(anchor) || (sentence.length >= MIN_PART_LENGTH && anchor.includes(sentence));
  });
  // 두 유형의 해석 문장이 같을 수 있다 — 앞 문장과 같은 유형을 먼저 고른다
  return candidates.find((a) => a.category === previous) ?? candidates[0];
}

/**
 * 기준 문장에 걸리지 않은 문장의 유형. 사실은 같은 문단의 다음 → 앞 기준 문장을 따르고(결론이 사례 문장
 * 앞에 온다), 신호는 앞 기준 문장을 따른다(뉴스 문장 뒤에 전망이 붙는다). 없으면 전체의 다음 → 앞.
 */
function fillCategories(items: Item[]): void {
  const known = items.filter((i) => i.category);
  for (const item of items.filter((i) => !i.category)) {
    const index = items.indexOf(item);
    const next = (i: Item) => items.indexOf(i) > index;
    const sameParagraph = (i: Item) => i.paragraph === item.paragraph;
    const after = known.find((i) => sameParagraph(i) && next(i));
    const before = [...known].reverse().find((i) => !next(i) && (sameParagraph(i) || item.tag === SIGNAL_TAG));
    item.category = (
      (item.tag === SIGNAL_TAG ? before ?? after : after ?? before)
      ?? known.find(next)
      ?? [...known].reverse().find((i) => !next(i))
    )?.category;
  }
}

/** 유형마다 [확인된 사실] 뒤 [참고 신호] — 유형 순서는 본문에 처음 나온 순서다. */
function regroup(paragraphs: Paragraph[], anchors: SentenceAnchor[]): Paragraph[] {
  const items: Item[] = paragraphs.flatMap((p, paragraph) => p.sentences.map((text) => ({ paragraph, tag: p.tag, text })));
  items.forEach((item, index) => {
    const anchor = matchAnchor(item.text, anchors, items[index - 1]?.category);
    if (anchor) Object.assign(item, { category: anchor.category, tag: anchor.tag });
    else if (FORECAST.test(item.text)) item.tag = SIGNAL_TAG;
  });
  if (!items.some((i) => i.category)) return paragraphs;
  fillCategories(items);
  const categories = [...new Set(items.map((i) => i.category))];
  const ordered = categories.flatMap((category) => [FACT_TAG, SIGNAL_TAG, ""].flatMap(
    (tag) => items.filter((i) => i.category === category && i.tag === tag),
  ));
  return ordered.map((item) => ({ tag: item.tag, sentences: [item.text] }));
}

// LLM이 문장마다 같은 표기를 다시 붙여도 표기 단위 문단은 하나다
function mergeSameTag(paragraphs: Paragraph[]): Paragraph[] {
  return paragraphs.reduce<Paragraph[]>((merged, paragraph) => {
    const last = merged.at(-1);
    if (last && paragraph.tag && last.tag === paragraph.tag) last.sentences.push(...paragraph.sentences);
    else merged.push({ ...paragraph, sentences: [...paragraph.sentences] });
    return merged;
  }, []);
}

function render({ tag, sentences }: Paragraph): string {
  const body = sentences.join(HARD_BREAK);
  return tag ? `${tag}${HARD_BREAK}${body}` : body;
}

export function gradedParagraphs(markdown: string, anchors: SentenceAnchor[] = []): string {
  if (!GRADE_TAG.test(markdown)) return markdown;
  const [, heading = "", body = ""] = markdown.match(LEADING_HEADING) ?? [];
  const paragraphs = body
    .replace(/\s+/g, " ")
    .split(BEFORE_GRADE_TAG)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map(parse);
  const unique = dropRepeats(paragraphs);
  const arranged = anchors.length > 0 ? regroup(unique, anchors) : movePastFacts(unique);
  return heading + mergeSameTag(arranged).map(render).join("\n\n");
}

export function analogAnchors(analogs: EventAnalogs | UnavailableFact | undefined): SentenceAnchor[] {
  const data = availableFact(analogs);
  if (!data) return [];
  const fact = (category: string, text: string | null | undefined): SentenceAnchor[] =>
    text ? [{ category, tag: FACT_TAG, text }] : [];
  return [
    ...[...data.current_events, ...data.analogs].flatMap((e) => [...fact(e.category, e.summary_sentence), ...fact(e.category, e.overlap_sentence)]),
    ...(data.outlooks ?? []).flatMap((o) => [...fact(o.category, o.condition_sentence), ...fact(o.category, o.recommended_sentence)]),
  ];
}
