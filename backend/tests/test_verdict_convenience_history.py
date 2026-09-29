"""편의점 이력 도메인 — 브랜드 사전(옛 이름·CU 경계), 승계 접기, 담배권 빈자리 격자 (업종 특화 신호 설계서 §5·§6)."""

from datetime import date

import pytest

from apps.verdict.domain.services.convenience_history import (
    Episode,
    RetailerRecord,
    address_key,
    brand_of,
    fold_successions,
)
from apps.verdict.domain.services.tobacco_gap import TOBACCO_GAP_RADIUS_M, GeoPoint, blocked_counts


@pytest.mark.parametrize("name, brand", [
    ("GS25 종각점", "GS25"), ("지에스25 세운점", "GS25"), ("LG25종로교남점", "GS25"), ("엘지25 장위점", "GS25"),
    ("CU 광진웰츠점", "CU"), ("씨유(CU) 청계센트럴점", "CU"), ("훼미리마트 서소문점", "CU"),
    ("(주)비지에프리테일 휘경센터점", "CU"),
    ("(주)코리아세븐 종각점", "세븐일레븐"), ("바이더웨이 옥수점", "세븐일레븐"), ("7-ELEVEN 명륜성대점", "세븐일레븐"),
    ("위드미군자점", "이마트24"), ("이마트24 성동대로점", "이마트24"),
    ("한국미니스톱(주) M안국역점", "미니스톱"),
    ("365플러스 동대문역점", "기타 체인"), ("로그인25노원점", "기타 체인"),
])
def test_편의점_브랜드와_옛_이름을_찾는다(name, brand):
    assert brand_of(name) == brand


@pytest.mark.parametrize("name", [
    "CUBE마트", "SCU상사", "세븐마트", "행복슈퍼", "(주)지에스리테일 GS수퍼 종로명륜점", "로그인 PC", "17-11번지 담배",
])
def test_편의점이_아닌_상호는_None이다(name):
    assert brand_of(name) is None


def _r(rid, open_, close=None, addr="서울특별시 강남구 역삼동 1", region="1168064000"):
    return RetailerRecord(rid, "GS25", region, open_, close, addr)


def test_폐업_전후_90일_안_같은_지번_새_지정은_한_에피소드로_잇는다():
    episodes = fold_successions([_r("a", date(2015, 1, 1), date(2020, 3, 1)), _r("b", date(2020, 2, 20))])
    assert episodes == [Episode("1168064000", date(2015, 1, 1), None, 2)]


def test_90일을_넘기면_따로_센다():
    episodes = fold_successions([_r("a", date(2015, 1, 1), date(2020, 3, 1)), _r("b", date(2020, 7, 1))])
    assert len(episodes) == 2


def test_영업_중인_자리에_새_지정이_오면_잇지_않는다():
    # 대형 건물 안 동시 영업 점포를 합치지 않는다
    episodes = fold_successions([_r("a", date(2015, 1, 1)), _r("b", date(2016, 1, 1))])
    assert len(episodes) == 2


def test_승계가_여러_번이면_한_줄로_이어진다():
    episodes = fold_successions([
        _r("a", date(2010, 1, 1), date(2013, 1, 1)),
        _r("b", date(2013, 1, 15), date(2018, 5, 1)),
        _r("c", date(2018, 5, 1), date(2024, 1, 1)),
    ])
    assert episodes == [Episode("1168064000", date(2010, 1, 1), date(2024, 1, 1), 3)]


def test_주소가_없거나_다르면_잇지_않는다():
    episodes = fold_successions([
        _r("a", date(2015, 1, 1), date(2020, 3, 1), addr=None),
        _r("b", date(2020, 3, 2), addr=None),
        _r("c", date(2020, 3, 2), addr="서울특별시 강남구 역삼동 2"),
    ])
    assert len(episodes) == 3


def test_동이_없거나_1990년_이전_개업은_버린다():
    episodes = fold_successions([_r("a", date(1900, 1, 1)), _r("b", date(2015, 1, 1), region=None), _r("c", date(2015, 1, 1))])
    assert episodes == [Episode("1168064000", date(2015, 1, 1), None, 1)]


def test_지번주소_공백을_정규화한다():
    assert address_key(" 서울특별시  강남구 역삼동 1 ") == "서울특별시 강남구 역삼동 1"
    assert address_key("   ") is None
    assert address_key(None) is None


_M = 1 / 111_320  # 위도 1m


def test_반경_50m_안에_소매인이_있으면_막힌_자리다():
    retailers = [GeoPoint(None, 37.5, 127.0)]
    candidates = [
        GeoPoint("r1", 37.5, 127.0),
        GeoPoint("r1", 37.5 + 40 * _M, 127.0),
        GeoPoint("r1", 37.5 + 60 * _M, 127.0),
        GeoPoint("r2", 37.6, 127.0),
        GeoPoint(None, 37.5, 127.0),  # 동 없는 후보는 버린다
    ]
    assert blocked_counts(candidates, retailers) == {"r1": (3, 2), "r2": (1, 0)}


def test_반경은_인자로_바꿀_수_있고_기본은_50m다():
    assert TOBACCO_GAP_RADIUS_M == 50.0
    assert blocked_counts([GeoPoint("r1", 37.5 + 60 * _M, 127.0)], [GeoPoint(None, 37.5, 127.0)], radius_m=100.0) == {"r1": (1, 1)}
