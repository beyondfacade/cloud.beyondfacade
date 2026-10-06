"""RagChunk 빌더 순수 함수 — funding 엔티티 → RagChunk 변환."""

from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.rag.domain.entities.rag_chunk_entity import build_funding_chunk


def _fake_program(**overrides) -> FundingProgram:
    defaults = dict(
        program_id="P1",
        source="bizinfo",
        title="제목",
        org="기관",
        url="https://example.com/p1",
        apply_period="상시",
    )
    defaults.update(overrides)
    return FundingProgram(**defaults)


def test_funding_chunk_concatenates_title_org_target_summary():
    program = _fake_program(
        title="청년창업자금",
        org="중기부",
        field_category="금융",
        target_text="예비창업자",
        hashtags="창업,대출",
        summary="저금리 융자",
    )
    chunk = build_funding_chunk(program)
    assert chunk.chunk_id == f"funding:{program.program_id}"
    for part in ["청년창업자금", "중기부", "금융", "예비창업자", "창업,대출", "저금리 융자"]:
        assert part in chunk.content
    assert chunk.url == program.url


def test_funding_chunk_treats_none_optional_fields_as_empty_string():
    program = _fake_program(
        field_category=None, target_text=None, hashtags=None, summary=None
    )
    chunk = build_funding_chunk(program)
    assert "None" not in chunk.content
