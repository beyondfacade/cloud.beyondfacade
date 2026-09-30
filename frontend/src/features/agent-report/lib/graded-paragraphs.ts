/** 근거 표기([확인된 사실]·[참고 신호]) 단위 문단 + 문장 단위 줄바꿈. LLM이 나눈 줄은 믿지 않고 다시 짠다. */

const GRADE_TAG = /\[(?:확인된 사실|참고 신호)\]/;
const BEFORE_GRADE_TAG = /(?=\[(?:확인된 사실|참고 신호)\])/;
// 한글 뒤 마침표만 문장 끝으로 본다 — "2.9%"·"10,320원" 같은 숫자 안 마침표는 자르지 않는다
const SENTENCE_END = /(?<=[가-힣][.!?])\s+/;
const LEADING_HEADING = /^(#{1,6}\s.*\n+)?([\s\S]*)$/;
// 마크다운 강제 줄바꿈 — 줄 끝 공백 두 칸
const HARD_BREAK = "  \n";

export function gradedParagraphs(markdown: string): string {
  if (!GRADE_TAG.test(markdown)) return markdown;
  const [, heading = "", body = ""] = markdown.match(LEADING_HEADING) ?? [];
  const paragraphs = body
    .replace(/\s+/g, " ")
    .split(BEFORE_GRADE_TAG)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => paragraph.split(SENTENCE_END).join(HARD_BREAK));
  return heading + paragraphs.join("\n\n");
}
