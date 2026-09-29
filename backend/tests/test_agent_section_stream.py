"""SectionSplitter — 스트림 조각을 [SECTION:name] 마커로 가르는 순수 분할기 (설계서 §3-3③)."""

from apps.agent.domain.services.section_stream import SectionSplitter, concat_sections


def _feed_all(splitter: SectionSplitter, pieces: list[str]) -> list[tuple[str, str]]:
    """조각을 순서대로 먹인 뒤 꼬리까지 비운다."""
    chunks: list[tuple[str, str]] = []
    for piece in pieces:
        chunks.extend(splitter.feed(piece))
    chunks.extend(splitter.flush())
    return chunks


def test_마커가_조각_경계에_걸쳐도_섹션을_알아본다():
    """토큰 스트림은 마커를 한 덩어리로 주지 않는다 — 걸친 마커를 놓치면 섹션이 통째로 사라진다."""
    splitter = SectionSplitter()

    chunks = _feed_all(splitter, ["[SECT", "ION:verd", "ict]판정 한 줄.", "[SECTION:reasons]이유."])

    assert chunks == [("verdict", "판정 한 줄."), ("reasons", "이유.")]


def test_첫_마커_앞_서문은_버린다():
    """도구 호출 전 잡담·머리말은 리포트 본문이 아니다 (설계서 §9)."""
    splitter = SectionSplitter()

    chunks = _feed_all(splitter, ["알겠습니다. 리포트를 작성합니다.\n", "[SECTION:verdict]판정."])

    assert chunks == [("verdict", "판정.")]


def test_서문만_오면_아무것도_내보내지_않는다():
    splitter = SectionSplitter()

    assert _feed_all(splitter, ["도구를 먼저 호출하겠습니다."]) == []
    assert splitter.sections_seen == []


def test_같은_마커가_다시_나오면_그_섹션에_이어_붙인다():
    """중복 마커는 섹션을 다시 열 뿐, 이미 흘려보낸 조각을 되돌리지 않는다(프론트는 append다)."""
    splitter = SectionSplitter()

    chunks = _feed_all(splitter, ["[SECTION:verdict]초안.", "[SECTION:verdict]최종본."])

    assert chunks == [("verdict", "초안."), ("verdict", "최종본.")]
    assert splitter.sections_seen == ["verdict"]


def test_한_글자씩_흘려도_한글이_깨지지_않고_순서대로_나온다():
    splitter = SectionSplitter()
    text = "[SECTION:verdict]🔴 비추천입니다.[SECTION:funding]공고 2건."

    chunks = _feed_all(splitter, list(text))

    sections = [section for section, _ in chunks]
    assert sections == sorted(sections, key=["verdict", "funding"].index)  # 순서가 섞이지 않는다
    assert set(sections) == {"verdict", "funding"}
    assert concat_sections(chunks) == "🔴 비추천입니다.\n\n공고 2건."


def test_섹션_앞뒤_공백은_털어낸다():
    """마커 바로 뒤 줄바꿈과 다음 마커 앞 줄바꿈은 본문이 아니다."""
    splitter = SectionSplitter()

    chunks = _feed_all(splitter, ["[SECTION:verdict]\n### 판정\n\n🔴 위험.\n[SECTION:reasons]\n이유.\n"])

    assert chunks == [("verdict", "### 판정\n\n🔴 위험."), ("reasons", "이유.")]


def test_마커가_아닌_대괄호는_붙들지_않고_흘린다():
    """[확인된 사실] 같은 본문 대괄호에서 스트림이 멎으면 글이 끊겨 보인다."""
    splitter = SectionSplitter()
    splitter.feed("[SECTION:reasons]")

    chunks = splitter.feed("[확인된 사실] 폐업률 12%.")

    assert chunks == [("reasons", "[확인된 사실] 폐업률 12%.")]


def test_sections_seen은_처음_나온_순서를_기억한다():
    splitter = SectionSplitter()

    _feed_all(splitter, ["[SECTION:verdict]가[SECTION:reasons]나[SECTION:verdict]다"])

    assert splitter.sections_seen == ["verdict", "reasons"]


def test_붙들고_있던_꼬리는_flush가_한_번만_낸다():
    """스트림이 마커 앞부분처럼 생긴 꼬리에서 끝나면 그 꼬리도 본문이다."""
    splitter = SectionSplitter()

    assert splitter.feed("[SECTION:verdict]판정 [SEC") == [("verdict", "판정")]
    assert splitter.flush() == [("verdict", " [SEC")]
    assert splitter.flush() == []


def test_concat_sections는_섹션별로_잇고_섹션끼리는_빈_줄로_나눈다():
    """저장하는 report_md는 조각 나열이 아니라 섹션 본문이어야 한다 (설계서 §3-3⑤)."""
    chunks = [("verdict", "🔴 "), ("verdict", "비추천."), ("reasons", "폐업률이 높다.")]

    assert concat_sections(chunks) == "🔴 비추천.\n\n폐업률이 높다."
