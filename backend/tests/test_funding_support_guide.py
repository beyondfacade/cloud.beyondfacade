"""창업 지원 정보 묶음 검증 — 구 전용 판정·업종 낱말·세 묶음 나누기 (DB 없음)."""

from datetime import date

from fastapi.testclient import TestClient

from apps.funding.app.dtos.funding_program_dto import RateDto
from apps.funding.app.ports.output.funding_program_port import (
    DistrictNameLookupPort,
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
    LatestRatesPort,
    SeoulDistrictNamesPort,
)
from apps.funding.app.use_cases.funding_program_interactor import FundingProgramInteractor
from apps.funding.dependencies.funding_program_dependencies import (
    get_funding_program_use_case,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.support_guide import (
    build_support_guide,
    industry_matched,
    mentioned_districts,
    open_to_district,
)
from main import app

_SEOUL_GU = frozenset({"종로구", "중구", "강남구", "관악구", "은평구", "서대문구"})
_TODAY = date(2026, 9, 30)


def _program(
    n: int,
    *,
    title: str | None = None,
    hashtags: str = "경영,서울",
    org: str = "서울특별시",
    target: str = "소상공인",
    field_category: str | None = "경영",
    deadline: date | None = date(2026, 12, 1),
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
    )


def _guide(programs, *, district="강남구", industry="korean_food"):
    return build_support_guide(
        programs,
        seoul_district_names=_SEOUL_GU,
        district_name=district,
        industry_id=industry,
        today=_TODAY,
    )


def _ids(items):
    return [item.candidate.program.program_id for item in items]


# --- 구 이름 찾기 ---


def test_제목에_적힌_구_이름을_찾는다():
    program = _program(1, title="[서울] 관악구 2026년 소상공인 원스톱 지원사업")

    assert mentioned_districts(program, _SEOUL_GU) == {"관악구"}


def test_태그와_소관기관의_구_이름도_찾는다():
    assert mentioned_districts(_program(1, hashtags="경영,서울,은평구"), _SEOUL_GU) == {"은평구"}
    assert mentioned_districts(_program(2, org="강남구"), _SEOUL_GU) == {"강남구"}


def test_낱말_안에_묻힌_구_이름은_구로_보지_않는다():
    # "집중구역"의 "중구"는 자치구가 아니다
    program = _program(1, title="상권 집중구역 소상공인 지원")

    assert mentioned_districts(program, _SEOUL_GU) == set()


def test_구청이라고_써도_구로_본다():
    program = _program(1, title="은평구청 청년식당 입점 모집")

    assert mentioned_districts(program, _SEOUL_GU) == {"은평구"}


# --- 업종 낱말 ---


def test_업종_낱말이_제목이나_태그에_있으면_업종_관련이다():
    assert industry_matched(_program(1, title="외식업 소상공인 배달비 지원"), "korean_food")
    assert industry_matched(_program(2, hashtags="경영,서울,식품접객업소"), "cafe")


def test_다른_낱말에_섞인_업종_낱말은_업종_관련이_아니다():
    # 2026-09-30 실측: 수출 공고 태그의 "미용기기"·"헬스케어"가 미용실·헬스장으로 잡혔다
    수출 = _program(1, hashtags="수출,서울,K-뷰티,미용기기,헬스케어", title="벤처기업 인도 시장진출")
    대학원 = _program(2, title="대학원 연계 창업 지원")

    assert not industry_matched(수출, "hair_salon")
    assert not industry_matched(수출, "gym")
    assert not industry_matched(대학원, "academy")


def test_업종_낱말이_없거나_모르는_업종이면_업종_관련이_아니다():
    assert not industry_matched(_program(1, title="소상공인 디지털 전환"), "korean_food")
    assert not industry_matched(_program(2, title="외식업 지원"), "unknown")
    assert not industry_matched(_program(3, title="외식업 지원"), None)


# --- 세 묶음 ---


def test_다른_구_전용_공고는_뺀다():
    guide = _guide([_program(1, title="관악구 소상공인 지원"), _program(2)])

    assert _ids(guide.district) + _ids(guide.loans) + _ids(guide.others) == ["p02"]


def test_우리_구_전용_공고는_구_묶음에_간다():
    guide = _guide([_program(1, title="강남구 소상공인 경영 지원"), _program(2)])

    assert _ids(guide.district) == ["p01"]
    assert _ids(guide.others) == ["p02"]
    assert guide.district[0].district_match is True


def test_금융_분야는_대출_묶음에_가고_우리_구_대출이_앞선다():
    서울대출 = _program(1, field_category="금융", deadline=date(2026, 10, 1))
    구대출 = _program(2, field_category="금융", title="강남구 소상공인 융자", deadline=date(2026, 11, 1))

    guide = _guide([서울대출, 구대출])

    assert _ids(guide.loans) == ["p02", "p01"]
    assert guide.district == []


def test_창업_경영_묶음은_업종_관련_공고가_앞선다():
    일반 = _program(1, deadline=date(2026, 10, 1))
    업종 = _program(2, title="외식업 소상공인 지원", deadline=date(2026, 11, 1))

    guide = _guide([일반, 업종])

    assert _ids(guide.others) == ["p02", "p01"]
    assert guide.others[0].industry_match is True


def test_구를_모르면_구_전용_공고를_모두_빼고_구_묶음은_비운다():
    guide = _guide([_program(1, title="강남구 소상공인 지원"), _program(2)], district=None)

    assert guide.district == []
    assert _ids(guide.others) == ["p02"]


def test_why는_후보_규칙_그대로이고_우리_구와_업종은_표시로만_준다():
    # 화면이 표시를 따로 단다 — why에 또 쓰면 같은 말이 두 번 보인다
    item = _guide([_program(1, title="강남구 외식업 소상공인 지원")]).district[0]

    assert item.why == "서울 · 소상공인 · 경영"
    assert (item.district_match, item.industry_match) == (True, True)


def test_묶음마다_상한이_있다():
    programs = [_program(n, deadline=date(2026, 10, n)) for n in range(1, 20)]

    assert len(_guide(programs).others) == 8


# --- 유스케이스·API ---


class _Repository(FundingProgramRepositoryPort):
    def __init__(self, programs):
        self._programs = programs

    def upsert(self, programs):
        raise NotImplementedError

    def refresh_expirations(self, today):
        raise NotImplementedError

    def list_open(self, limit):
        raise NotImplementedError

    def list_open_all(self):
        return self._programs


class _Gateway(FundingSearchGatewayPort):
    def fetch_all(self):
        return []


class _Districts(SeoulDistrictNamesPort, DistrictNameLookupPort):
    def names(self):
        return _SEOUL_GU

    def name_of(self, district_code):
        return {"11680": "강남구"}.get(district_code)


class _Rates(LatestRatesPort):
    def latest(self):
        return [RateDto(rate_type="base", period="202608", rate_pct=2.5)]


def _interactor(programs):
    districts = _Districts()
    return FundingProgramInteractor(
        repository=_Repository(programs),
        gateway=_Gateway(),
        seoul_districts=districts,
        district_lookup=districts,
        rates=_Rates(),
    )


def test_동_코드_앞_다섯_자리로_구를_찾아_묶는다():
    guide = _interactor([_program(1, title="강남구 소상공인 지원")]).support_guide(
        "1168064000", "korean_food"
    )

    assert guide.district_name == "강남구"
    assert [item.program.program_id for item in guide.district] == ["p01"]
    assert guide.rates == [RateDto(rate_type="base", period="202608", rate_pct=2.5)]


def test_동_코드가_없어도_묶음을_돌려준다():
    guide = _interactor([_program(1)]).support_guide(None, None)

    assert guide.district_name is None
    assert [item.program.program_id for item in guide.others] == ["p01"]


def test_구_전용이_아니거나_우리_구_전용이면_열려_있다():
    assert open_to_district(_program(1), _SEOUL_GU, "강남구")
    assert open_to_district(_program(2, title="강남구 소상공인 지원"), _SEOUL_GU, "강남구")
    assert not open_to_district(_program(3, title="관악구 소상공인 지원"), _SEOUL_GU, "강남구")
    assert not open_to_district(_program(4, title="강남구 소상공인 지원"), _SEOUL_GU, None)


def test_공고_후보는_동을_주면_다른_구_전용을_빼고_상한을_채운다():
    다른구 = [_program(n, title=f"관악구 지원 {n}", deadline=date(2026, 10, n)) for n in range(1, 9)]
    우리구 = _program(9, title="강남구 소상공인 지원", deadline=date(2026, 11, 1))
    일반 = [_program(n, deadline=date(2026, 11, n)) for n in range(10, 20)]
    interactor = _interactor([*다른구, 우리구, *일반])

    picked = [c.program.program_id for c in interactor.list_candidates("korean_food", None, None, "1168064000").candidates]

    assert len(picked) == 8
    assert "p09" in picked
    assert not any(p in picked for p in [f"p{n:02d}" for n in range(1, 9)])


def test_공고_후보는_동이_없으면_지금처럼_거르지_않는다():
    interactor = _interactor([_program(1, title="관악구 소상공인 지원")])

    assert [c.program.program_id for c in interactor.list_candidates(None, None, None).candidates] == ["p01"]


def test_공고_후보는_모르는_동이면_구_전용을_모두_뺀다():
    interactor = _interactor([_program(1, title="강남구 소상공인 지원"), _program(2)])

    picked = interactor.list_candidates(None, None, None, "9999999999").candidates

    assert [c.program.program_id for c in picked] == ["p02"]


def test_공고_후보_API는_동을_받아_다른_구_전용을_뺀다():
    app.dependency_overrides[get_funding_program_use_case] = lambda: _interactor(
        [_program(1, title="관악구 소상공인 지원"), _program(2)]
    )
    try:
        response = TestClient(app).get("/funding/candidates?industry=korean_food&region=1168064000")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [c["program_id"] for c in response.json()["candidates"]] == ["p02"]


def test_지원_정보_API는_세_묶음과_금리를_돌려준다():
    app.dependency_overrides[get_funding_program_use_case] = lambda: _interactor(
        [_program(1, title="강남구 소상공인 지원"), _program(2, field_category="금융")]
    )
    try:
        response = TestClient(app).get("/funding/support?region=1168064000&industry=korean_food")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["district_name"] == "강남구"
    assert body["industry_id"] == "korean_food"
    assert [p["program_id"] for p in body["district"]] == ["p01"]
    assert [p["program_id"] for p in body["loans"]] == ["p02"]
    assert body["district"][0]["district_match"] is True
    assert body["rates"] == [{"rate_type": "base", "period": "202608", "rate_pct": 2.5}]
