"""section_stream — 리포트 절 조각을 저장용 마크다운으로 잇는다 (계약 순서 정렬)."""

from apps.agent.domain.services.section_stream import SECTION_ORDER, concat_sections


def test_concat_sections는_섹션별로_잇고_섹션끼리는_빈_줄로_나눈다():
    """저장하는 report_md는 조각 나열이 아니라 섹션 본문이어야 한다 (설계서 §3-3⑤)."""
    chunks = [("verdict", "🔴 "), ("verdict", "비추천."), ("reasons", "폐업률이 높다.")]

    assert concat_sections(chunks) == "🔴 비추천.\n\n폐업률이 높다."


def test_concat_sections는_도착_순서가_뒤섞여도_계약_순서로_저장한다():
    """폴백 섹션은 LLM이 쓴 섹션 뒤에 붙는다 — 저장본까지 그 순서면 글이 뒤엉킨다 (설계서 §5)."""
    chunks = [("funding", "공고."), ("verdict", "판정."), ("reasons", "이유.")]

    assert concat_sections(chunks) == "판정.\n\n이유.\n\n공고."


def test_concat_sections는_모르는_섹션도_버리지_않는다():
    chunks = [("stray", "미지의 절."), ("verdict", "판정.")]

    assert concat_sections(chunks) == "판정.\n\n미지의 절."


def test_섹션_순서_상수는_해석_다음_코드_절_순서다():
    """두 벌이 어긋나면 저장 순서와 방출 순서가 갈린다 — 해석은 늦게 오지만 저장본은 맨 위다."""
    from apps.agent.domain.services.report_sections import SECTION_TITLES

    assert SECTION_ORDER == ("answer", *SECTION_TITLES)
