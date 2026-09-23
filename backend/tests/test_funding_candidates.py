"""후보 공고 선별 검증 — 지역 판정·대상·정렬·상위 8 (설계서 §3, DB 없음)."""

from datetime import date

import pytest

from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.candidates import select_candidates
from apps.funding.domain.services.region_filter import (
    REGION_NATIONWIDE,
    REGION_SEOUL,
    SIDO_NAMES,
    classify_region,
    is_outside_seoul_local_gov,
)

_SEOUL_GU = frozenset({"종로구", "중구", "강남구", "관악구", "은평구"})
_ALL_SIDO = ",".join(SIDO_NAMES)
_TODAY = date(2026, 9, 24)


def _program(
    n: int,
    *,
    hashtags: str = "금융,서울",
    org: str = "중소벤처기업부",
    target: str = "소상공인",
    field_category: str | None = "금융",
    deadline: date | None = date(2026, 12, 1),
    is_expired: bool = False,
    title: str | None = None,
) -> FundingProgram:
    return FundingProgram(
        program_id=f"p{n:02d}",
        source="bizinfo",
        title=title or f"공고 {n}",
        org=org,
        url=f"https://example.com/{n}",
        apply_period="",
        target_text=target,
        hashtags=hashtags,
        field_category=field_category,
        deadline=deadline,
        is_expired=is_expired,
    )


def _select(programs, **kwargs):
    return select_candidates(
        programs, seoul_district_names=_SEOUL_GU, today=_TODAY, **kwargs
    )


# --- 지역 판정 ---


def test_서울_태그만_있으면_서울_전용이다():
    assert classify_region("금융,서울,2026", "중소벤처기업부", _SEOUL_GU) == REGION_SEOUL


def test_시도_17개가_전부_붙으면_전국이다():
    # 전국 공고는 "시도 언급 없음"이 아니라 시도를 전부 단다 (2026-09-24 실측)
    assert classify_region(f"금융,{_ALL_SIDO}", "중소벤처기업부", _SEOUL_GU) == REGION_NATIONWIDE


def test_통합_표기_전남광주는_전남과_광주로_펴서_센다():
    """원천이 시도 어휘를 두 벌 섞어 쓴다 — 태그 수만 세면 16개짜리 전국 공고를 놓친다."""
    merged = ",".join(s for s in SIDO_NAMES if s not in ("전남", "광주")) + ",전남광주"

    assert len(merged.split(",")) == 16
    assert classify_region(f"창업,{merged}", "중소벤처기업부", _SEOUL_GU) == REGION_NATIONWIDE


def test_시도_하나가_빠지면_전국이_아니다():
    거의전부 = ",".join(s for s in SIDO_NAMES if s != "제주")

    assert classify_region(f"창업,{거의전부}", "중소벤처기업부", _SEOUL_GU) == REGION_SEOUL


def test_전국_태그도_전국이다():
    assert classify_region("경영,전국", "중소벤처기업부", _SEOUL_GU) == REGION_NATIONWIDE


def test_타_시도만_붙으면_해당_없음이다():
    assert classify_region("경영,경북,게임", "경상북도", _SEOUL_GU) is None


def test_서울_밖_지자체_공고는_시도를_다_달아도_제외된다():
    # 과천시 이자차액보전 — 태그로는 전국이지만 지자체 예산이라 서울 창업자와 무관하다
    assert classify_region(f"금융,{_ALL_SIDO},과천시", "과천시", _SEOUL_GU) is None


def test_서울_자치구와_서울특별시는_지자체_제외에_걸리지_않는다():
    assert is_outside_seoul_local_gov("강남구", _SEOUL_GU) is False
    assert is_outside_seoul_local_gov("서울특별시", _SEOUL_GU) is False
    assert is_outside_seoul_local_gov("중소벤처기업부", _SEOUL_GU) is False
    assert is_outside_seoul_local_gov("과천시", _SEOUL_GU) is True


# --- 선별·정렬 ---


def test_대상_키워드가_없으면_후보가_아니다():
    assert _select([_program(1, target="중소기업", title="중소기업 공고")]) == []


def test_대상은_제목에서도_찾는다():
    # 원천이 target_text를 비워두는 공고가 많다
    selected = _select([_program(1, target="", title="2026년 소상공인 지원 공고")])

    assert len(selected) == 1 and selected[0].audience == "소상공인"


def test_만료_플래그와_마감일을_모두_본다():
    # 만료 배치가 늦으면 플래그만으로는 지난 공고가 남는다 — 상담 자료에 들어가면 그 자체로 결함
    지난공고 = _program(1, deadline=date(2026, 9, 1))
    만료플래그 = _program(2, is_expired=True)
    유효 = _program(3, deadline=date(2026, 10, 1))

    assert [c.program.program_id for c in _select([지난공고, 만료플래그, 유효])] == ["p03"]


def test_서울_전용이_전국보다_앞선다():
    전국 = _program(1, hashtags=f"금융,{_ALL_SIDO}", deadline=date(2026, 10, 1))
    서울 = _program(2, hashtags="금융,서울", deadline=date(2026, 12, 1))

    assert [c.region for c in _select([전국, 서울])] == [REGION_SEOUL, REGION_NATIONWIDE]


def test_같은_지역이면_우선_분야가_앞서고_그다음_마감_임박순이다():
    비우선 = _program(1, field_category="수출", deadline=date(2026, 10, 1))
    우선늦음 = _program(2, field_category="금융", deadline=date(2026, 11, 1))
    우선이름 = _program(3, field_category="창업", deadline=date(2026, 10, 15))

    assert [c.program.program_id for c in _select([비우선, 우선늦음, 우선이름])] == [
        "p03",
        "p02",
        "p01",
    ]


def test_상시_공고는_마감_있는_공고보다_뒤다():
    상시 = _program(1, deadline=None)
    마감 = _program(2, deadline=date(2026, 12, 31))

    assert [c.program.program_id for c in _select([상시, 마감])] == ["p02", "p01"]


def test_창업_단계가_정렬_가점으로_작동한다():
    소상공인 = _program(1, target="소상공인", deadline=date(2026, 12, 1))
    예비창업 = _program(2, target="예비창업자 대상", deadline=date(2026, 12, 1))

    앞선다 = lambda stage: _select([소상공인, 예비창업], stage=stage)[0].program.program_id
    assert 앞선다("pre") == "p02"
    assert 앞선다("registered") == "p01"


def test_알_수_없는_단계는_가점_없이_동작한다():
    # 필터가 아니라 가점이라 모르는 값이 와도 결과가 비지 않는다
    assert len(_select([_program(1)], stage="unknown-stage")) == 1


def test_상위_8건까지만_돌려준다():
    programs = [_program(n, deadline=date(2026, 10, n + 1)) for n in range(1, 15)]

    assert len(_select(programs)) == 8


def test_why는_걸린_규칙을_말하고_같은_말을_두_번_쓰지_않는다():
    일반 = _select([_program(1, target="소상공인", field_category="금융")])[0]
    겹침 = _select([_program(2, target="창업 기업", field_category="창업")])[0]

    assert 일반.why == "서울 · 소상공인 · 금융"
    assert 겹침.why == "서울 · 창업"


def test_우선_분야가_아니면_why에_분야를_쓰지_않는다():
    selected = _select([_program(1, field_category="수출")])[0]

    assert selected.why == "서울 · 소상공인"


@pytest.mark.parametrize("limit", [0, 1, 3])
def test_limit이_그대로_적용된다(limit):
    programs = [_program(n) for n in range(1, 6)]

    assert len(_select(programs, limit=limit)) == limit
