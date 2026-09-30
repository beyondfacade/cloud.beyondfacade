/** 근거 표기([확인된 사실]·[참고 신호]) 단위 문단 + 표기 뒤·문장 단위 줄바꿈. LLM이 나눈 줄은 믿지 않고 다시 짠다. */

const GRADE_TAG = /\[(?:확인된 사실|참고 신호)\]/;
const BEFORE_GRADE_TAG = /(?=\[(?:확인된 사실|참고 신호)\])/;
const LEADING_TAG = /^(\[(?:확인된 사실|참고 신호)\])\s*/;
const FACT_TAG = "[확인된 사실]";
const SIGNAL_TAG = "[참고 신호]";
// 한글 뒤 마침표만 문장 끝으로 본다 — "2.9%"·"10,320원" 같은 숫자 안 마침표는 자르지 않는다
const SENTENCE_END = /(?<=[가-힣][.!?])\s+/;
// 사례 속 강세 업종 문장은 과거 값이라 [확인된 사실]이다 — LLM이 [참고 신호] 뒤에 붙여도 옮긴다
const PAST_FACT = /상대적으로 잘 버/;
const LEADING_HEADING = /^(#{1,6}\s.*\n+)?([\s\S]*)$/;
// 마크다운 강제 줄바꿈 — 줄 끝 공백 두 칸
const HARD_BREAK = "  \n";

interface Paragraph {
  tag: string;
  sentences: string[];
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

// LLM이 문장마다 같은 표기를 다시 붙여도 표기 단위 문단은 하나다
function mergeSameTag(paragraphs: Paragraph[]): Paragraph[] {
  return paragraphs.reduce<Paragraph[]>((merged, paragraph) => {
    const last = merged.at(-1);
    if (last && paragraph.tag && last.tag === paragraph.tag) last.sentences.push(...paragraph.sentences);
    else merged.push(paragraph);
    return merged;
  }, []);
}

function render({ tag, sentences }: Paragraph): string {
  const body = sentences.join(HARD_BREAK);
  return tag ? `${tag}${HARD_BREAK}${body}` : body;
}

export function gradedParagraphs(markdown: string): string {
  if (!GRADE_TAG.test(markdown)) return markdown;
  const [, heading = "", body = ""] = markdown.match(LEADING_HEADING) ?? [];
  const paragraphs = body
    .replace(/\s+/g, " ")
    .split(BEFORE_GRADE_TAG)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map(parse);
  return heading + mergeSameTag(movePastFacts(paragraphs)).map(render).join("\n\n");
}
