"""Driven Adapter — rag BC의 질문 유사도 정렬 (cross-BC ACL, rag 접근은 이 파일 안에서만).

공고 1건 = 청크 `funding:{program_id}` 1개(bge-m3, 매일 증분 색인). 접두를 붙여 부르고 떼어 되돌린다.
임베딩 실패(Ollama 다운·타임아웃)는 예외 그대로 올린다 — 규칙 순서로 되돌리는 판단은 인터랙터가 한다.
"""

from apps.funding.app.ports.output.funding_program_port import QuestionRankerPort
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case

_CHUNK_PREFIX = "funding:"
_PROVIDER = "bge-m3"  # 색인과 같은 모델이어야 한다
# 지원사업 화면·리포트가 기다리는 경로 — Ollama가 멈추면 5초 뒤 규칙 순서로 돌아간다(설계서 §2-4).
# 모델 콜드 로드는 실측 약 2초(10/7)
_QUERY_TIMEOUT_SECONDS = 5.0


class RagQuestionRankerGateway(QuestionRankerPort):
    def rank(self, question: str, program_ids: list[str]) -> list[str]:
        chunk_ids = [f"{_CHUNK_PREFIX}{program_id}" for program_id in program_ids]
        ranked = get_rag_search_use_case(_PROVIDER, timeout=_QUERY_TIMEOUT_SECONDS).rank_within(question, chunk_ids)
        return [chunk_id.removeprefix(_CHUNK_PREFIX) for chunk_id in ranked]
