/** 받침 유무로 주제 조사(은/는)를 붙인다. 한글이 아니면 '는'. 백엔드 intent BC의 조사 함수와 같은 규칙. */
export function withTopicParticle(word: string): string {
  const last = word.charCodeAt(word.length - 1);
  if (last < 0xac00 || last > 0xd7a3) return `${word}는`;
  return (last - 0xac00) % 28 === 0 ? `${word}는` : `${word}은`;
}
