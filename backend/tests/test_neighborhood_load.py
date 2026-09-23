"""neighborhood 동네 맥락 7종 적재 검증 — CP949 파싱 · 컬럼 이름 매핑 · 전개 · region · 멱등.

고정하는 실측 사실 (설계서 §2~§4, 2026-09-23 확보분).
- 인코딩 CP949, 시점 컬럼 `기준_년분기_코드` 5자리 **문자열**
- **소비는 `음식_지출_총금액`이 `기타_지출_총금액` 뒤에 온다** — 순서로 매핑하면 뒤바뀐다
- 유동인구 시간대는 밑줄(`시간대_00_06`), 저장 dim_key는 commerce와 같은 `00_06`
- 직장은 접미사 `_직장_인구_수`, 상주는 `_상주인구_수` — 모양이 다르다
- 직장인구는 414개 동뿐이다. 없는 동의 행을 만들지 않는다
- 서울 평균은 분기에만 의존한다 — 9,350행에서 22행으로 중복 제거된다
"""

from pathlib import Path

from sqlalchemy import delete, func, select

from apps.neighborhood.adapter.outbound.gateways.seoul_neighborhood_csv_gateway import (
    APARTMENT_DIMENSIONS,
    FACILITY_COLUMNS,
    SPENDING_COLUMNS,
    SeoulApartmentHouseholdCsvGateway,
    SeoulCommerceChangeBaselineCsvGateway,
    SeoulCommerceChangeCsvGateway,
    SeoulFacilityCsvGateway,
    SeoulFootfallCsvGateway,
    SeoulHousingAverageCsvGateway,
    SeoulResidentHouseholdCsvGateway,
    SeoulResidentPopulationCsvGateway,
    SeoulSpendingCsvGateway,
    SeoulWorkerPopulationCsvGateway,
)
from apps.neighborhood.adapter.outbound.orms.region_commerce_change_orm import (
    RegionCommerceChangeOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_footfall_quarter_orm import (
    RegionFootfallQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm import (
    SeoulCommerceChangeBaselineOrm,
)
from apps.neighborhood.adapter.outbound.repositories.region_commerce_change_repository import (
    SqlAlchemyRegionCommerceChangeRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_footfall_quarter_repository import (
    SqlAlchemyRegionFootfallQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.seoul_commerce_change_baseline_repository import (
    SqlAlchemySeoulCommerceChangeBaselineRepository,
)
from apps.neighborhood.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.neighborhood.app.use_cases.region_footfall_quarter_interactor import (
    RegionFootfallQuarterIngestInteractor,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import RegionCommerceChange
from apps.neighborhood.domain.entities.region_footfall_quarter_entity import RegionFootfallQuarter
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_ADSTRD = "99999999"
_TEST_QUARTER = "29991"

# ---------- 실 원천 헤더 실측 사본 (2026-09-23 확보분) ----------

FOOTFALL_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,총_유동인구_수,남성_유동인구_수,여성_유동인구_수,"
    "연령대_10_유동인구_수,연령대_20_유동인구_수,연령대_30_유동인구_수,연령대_40_유동인구_수,"
    "연령대_50_유동인구_수,연령대_60_이상_유동인구_수,시간대_00_06_유동인구_수,"
    "시간대_06_11_유동인구_수,시간대_11_14_유동인구_수,시간대_14_17_유동인구_수,"
    "시간대_17_21_유동인구_수,시간대_21_24_유동인구_수,월요일_유동인구_수,화요일_유동인구_수,"
    "수요일_유동인구_수,목요일_유동인구_수,금요일_유동인구_수,토요일_유동인구_수,일요일_유동인구_수"
)
WORKER_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,총_직장_인구_수,남성_직장_인구_수,"
    "여성_직장_인구_수,연령대_10_직장_인구_수,연령대_20_직장_인구_수,연령대_30_직장_인구_수,"
    "연령대_40_직장_인구_수,연령대_50_직장_인구_수,연령대_60_이상_직장_인구_수,"
    "남성연령대_10_직장_인구_수,남성연령대_20_직장_인구_수,남성연령대_30_직장_인구_수,"
    "남성연령대_40_직장_인구_수,남성연령대_50_직장_인구_수,남성연령대_60_이상_직장_인구_수,"
    "여성연령대_10_직장_인구_수,여성연령대_20_직장_인구_수,여성연령대_30_직장_인구_수,"
    "여성연령대_40_직장_인구_수,여성연령대_50_직장_인구_수,여성연령대_60_이상_직장_인구_수"
)
RESIDENT_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,총_상주인구_수,남성_상주인구_수,"
    "여성_상주인구_수,연령대_10_상주인구_수,연령대_20_상주인구_수,연령대_30_상주인구_수,"
    "연령대_40_상주인구_수,연령대_50_상주인구_수,연령대_60_이상_상주인구_수,"
    "남성연령대_10_상주인구_수,남성연령대_20_상주인구_수,남성연령대_30_상주인구_수,"
    "남성연령대_40_상주인구_수,남성연령대_50_상주인구_수,남성연령대_60_이상_상주인구_수,"
    "여성연령대_10_상주인구_수,여성연령대_20_상주인구_수,여성연령대_30_상주인구_수,"
    "여성연령대_40_상주인구_수,여성연령대_50_상주인구_수,여성연령대_60_이상_상주인구_수,"
    "총_가구_수,아파트_가구_수,비_아파트_가구_수"
)
FACILITY_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,집객시설_수,관공서_수,은행_수,종합병원_수,"
    "일반_병원_수,약국_수,유치원_수,초등학교_수,중학교_수,고등학교_수,대학교_수,백화점_수,"
    "슈퍼마켓_수,극장_수,숙박_시설_수,공항_수,철도_역_수,버스_터미널_수,지하철_역_수,버스_정거장_수"
)
SPENDING_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,지출_총금액,식료품_지출_총금액,"
    "의류_신발_지출_총금액,생활용품_지출_총금액,의료비_지출_총금액,교통_지출_총금액,"
    "교육_지출_총금액,유흥_지출_총금액,여가_문화_지출_총금액,기타_지출_총금액,음식_지출_총금액"
)
APARTMENT_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,아파트_단지_수,"
    "아파트_면적_66_제곱미터_미만_세대_수,아파트_면적_66_제곱미터_세대_수,"
    "아파트_면적_99_제곱미터_세대_수,아파트_면적_132_제곱미터_세대_수,"
    "아파트_면적_165_제곱미터_세대_수,아파트_가격_1_억_미만_세대_수,아파트_가격_1_억_세대_수,"
    "아파트_가격_2_억_세대_수,아파트_가격_3_억_세대_수,아파트_가격_4_억_세대_수,"
    "아파트_가격_5_억_세대_수,아파트_가격_6_억_이상_세대_수,아파트_평균_면적,아파트_평균_시가"
)
CHANGE_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,상권_변화_지표,상권_변화_지표_명,"
    "운영_영업_개월_평균,폐업_영업_개월_평균,서울_운영_영업_개월_평균,서울_폐업_영업_개월_평균"
)


def _cp949_csv(tmp_path: Path, name: str, header: str, *rows: str) -> Path:
    """원천은 CP949 + LF다. UTF-8로 읽으면 첫 줄부터 깨진다."""
    path = tmp_path / name
    path.write_bytes(("\n".join([header, *rows]) + "\n").encode("cp949"))
    return path


# ---------- 유동인구: CP949 · 년분기 문자열 보존 · 22행 전개 ----------


def test_footfall_row_expands_to_22_dimension_rows_with_normalized_keys(tmp_path):
    """시간대 dim_key는 원천 밑줄 표기 그대로 `00_06` — commerce 분해와 같은 표기로 맞춘다."""
    # 값은 자리마다 다르게 둬 어느 컬럼이 어느 구간에 붙는지 값으로 식별한다
    values = [str(100 + offset) for offset in range(22)]
    row = ",".join(["20251", "11110515", "청운효자동", *values])
    path = _cp949_csv(tmp_path, "footfall.csv", FOOTFALL_HEADER, row)

    rows = list(SeoulFootfallCsvGateway().fetch_footfall(path))
    assert len(rows) == 22

    sizes: dict[str, int] = {}
    for entity in rows:
        sizes[entity.dim_type] = sizes.get(entity.dim_type, 0) + 1
    assert sizes == {"total": 1, "gender": 2, "age": 6, "hour": 6, "dow": 7}

    by_key = {(entity.dim_type, entity.dim_key): entity.headcount for entity in rows}
    assert by_key[("total", "all")] == 100
    assert by_key[("gender", "male")] == 101
    assert by_key[("gender", "female")] == 102
    assert by_key[("age", "10")] == 103
    assert by_key[("age", "60_over")] == 108
    assert by_key[("hour", "00_06")] == 109  # 시간대_00_06_유동인구_수
    assert by_key[("hour", "21_24")] == 114
    assert by_key[("dow", "mon")] == 115
    assert by_key[("dow", "sun")] == 121

    assert {entity.year_quarter for entity in rows} == {"20251"}  # 정수가 아니라 문자열
    assert {entity.adstrd_code for entity in rows} == {"11110515"}
    assert all(entity.region_code is None for entity in rows)  # 해석은 인터랙터 몫


def test_footfall_reads_cp949_and_keeps_leading_zero_quarters(tmp_path):
    """한글 동명이 CP949로 들어와도 깨지지 않고, 년분기는 5자리 문자열 그대로다."""
    row = ",".join(["20211", "11110515", "청운효자동", *["1"] * 22])
    path = _cp949_csv(tmp_path, "footfall.csv", FOOTFALL_HEADER, row)
    rows = list(SeoulFootfallCsvGateway().fetch_footfall(path))
    assert rows[0].year_quarter == "20211"
    assert isinstance(rows[0].year_quarter, str)


def test_blank_measures_stay_null_not_zero(tmp_path):
    """'0명'과 '집계 없음'은 다르다 — 0으로 채우지 않는다."""
    row = ",".join(["20251", "11110515", "청운효자동", *[""] * 22])
    path = _cp949_csv(tmp_path, "footfall.csv", FOOTFALL_HEADER, row)
    rows = list(SeoulFootfallCsvGateway().fetch_footfall(path))
    assert len(rows) == 22
    assert all(entity.headcount is None for entity in rows)


def test_missing_source_column_fails_loudly(tmp_path):
    """컬럼명이 바뀌면 값만 조용히 비는 대신 즉시 깨져야 한다."""
    broken = FOOTFALL_HEADER.replace("시간대_00_06_유동인구_수", "시간대_00~06_유동인구_수")
    row = ",".join(["20251", "11110515", "청운효자동", *["1"] * 22])
    path = _cp949_csv(tmp_path, "footfall.csv", broken, row)
    try:
        list(SeoulFootfallCsvGateway().fetch_footfall(path))
    except ValueError as error:
        assert "시간대_00_06_유동인구_수" in str(error)
    else:
        raise AssertionError("헤더에 없는 컬럼이면 ValueError여야 한다")


# ---------- 직장·상주인구: 접미사 차이 · 21행 전개 ----------


def _population_row(quarter: str, adstrd: str) -> str:
    return ",".join([quarter, adstrd, "청운효자동", *[str(200 + i) for i in range(21)]])


def test_worker_and_resident_share_axes_but_differ_in_column_suffix(tmp_path):
    """직장 `_직장_인구_수` · 상주 `_상주인구_수` — 접미사만 다르고 축 21개는 같다(§3-3)."""
    worker_path = _cp949_csv(
        tmp_path, "worker.csv", WORKER_HEADER, _population_row("20251", "11110515")
    )
    resident_path = _cp949_csv(
        tmp_path,
        "resident.csv",
        RESIDENT_HEADER,
        _population_row("20251", "11110515") + ",900,901,902",
    )

    workers = list(SeoulWorkerPopulationCsvGateway().fetch_population(worker_path))
    residents = list(SeoulResidentPopulationCsvGateway().fetch_population(resident_path))
    assert len(workers) == len(residents) == 21
    assert {entity.population_type for entity in workers} == {"worker"}
    assert {entity.population_type for entity in residents} == {"resident"}

    axes = {(entity.dim_type, entity.dim_key) for entity in workers}
    assert axes == {(entity.dim_type, entity.dim_key) for entity in residents}
    assert ("gender_age", "female_60_over") in axes
    assert ("gender_age", "male_10") in axes
    assert len([key for key in axes if key[0] == "gender_age"]) == 12

    by_key = {(entity.dim_type, entity.dim_key): entity.headcount for entity in workers}
    assert by_key[("total", "all")] == 200
    assert by_key[("gender", "male")] == 201
    assert by_key[("age", "10")] == 203
    assert by_key[("gender_age", "male_10")] == 209  # 남성연령대_10_직장_인구_수
    assert by_key[("gender_age", "female_60_over")] == 220


def test_worker_source_keeps_only_dong_present_in_file(tmp_path):
    """직장인구는 414개 동뿐이다 — 없는 동의 행을 지어내지 않는다(설계서 §3-2)."""
    path = _cp949_csv(
        tmp_path,
        "worker.csv",
        WORKER_HEADER,
        _population_row("20251", "11110515"),
        _population_row("20251", "11110530"),
    )
    rows = list(SeoulWorkerPopulationCsvGateway().fetch_population(path))
    assert {entity.adstrd_code for entity in rows} == {"11110515", "11110530"}
    assert len(rows) == 42  # 2행 × 21, 빠진 동을 채운 행은 없다


# ---------- 가구·아파트 ----------


def test_resident_household_columns_go_to_household_table(tmp_path):
    """가구 3종은 인구가 아니라 주거 스톡이라 household dim_type으로 간다."""
    path = _cp949_csv(
        tmp_path,
        "resident.csv",
        RESIDENT_HEADER,
        _population_row("20251", "11110515") + ",900,901,902",
    )
    rows = list(SeoulResidentHouseholdCsvGateway().fetch_households(path))
    assert [(entity.dim_type, entity.dim_key, entity.value) for entity in rows] == [
        ("household", "total", 900),
        ("household", "apartment", 901),
        ("household", "non_apartment", 902),
    ]


def _apartment_row(quarter: str, adstrd: str) -> str:
    return ",".join([quarter, adstrd, "청운효자동", *[str(300 + i) for i in range(13)], "56.5", "261960069"])


def test_apartment_expands_to_13_stock_rows_and_separate_average_row(tmp_path):
    """평균 면적·시가는 단위가 달라 세대 수와 같은 값 컬럼에 담지 않는다(§4-3 미확정 1 결정)."""
    path = _cp949_csv(tmp_path, "apartment.csv", APARTMENT_HEADER, _apartment_row("20251", "11110515"))

    stock = list(SeoulApartmentHouseholdCsvGateway().fetch_households(path))
    assert len(stock) == 13
    assert [(entity.dim_type, entity.dim_key) for entity in stock] == [
        (dim_type, dim_key) for dim_type, dim_key, _ in APARTMENT_DIMENSIONS
    ]
    by_key = {(entity.dim_type, entity.dim_key): entity.value for entity in stock}
    assert by_key[("apartment_complex", "count")] == 300
    assert by_key[("apartment_area", "under_66")] == 301
    assert by_key[("apartment_area", "165")] == 305
    assert by_key[("apartment_price", "under_100m")] == 306
    assert by_key[("apartment_price", "over_600m")] == 312

    averages = list(SeoulHousingAverageCsvGateway().fetch_housing_averages(path))
    assert len(averages) == 1
    assert averages[0].avg_area_m2 == 56.5  # 실수 — 세대 수 컬럼에 담을 수 없다
    assert averages[0].avg_price == 261960069
    assert averages[0].year_quarter == "20251"


# ---------- 집객시설 ----------


def test_facility_expands_to_total_plus_19_types(tmp_path):
    values = [str(400 + offset) for offset in range(20)]
    row = ",".join(["20251", "11110515", "청운효자동", *values])
    path = _cp949_csv(tmp_path, "facility.csv", FACILITY_HEADER, row)

    rows = list(SeoulFacilityCsvGateway().fetch_facilities(path))
    assert len(rows) == 20
    assert [entity.facility_type for entity in rows] == [name for name, _ in FACILITY_COLUMNS]
    by_type = {entity.facility_type: entity.facility_count for entity in rows}
    assert by_type["total"] == 400  # 원천 집객시설_수
    assert by_type["government"] == 401
    assert by_type["bus_stop"] == 419


def test_facility_blank_stays_null(tmp_path):
    """집객시설은 공란이 흔하다 — '시설 0개'로 바꾸면 없는 사실을 지어내는 것이다."""
    row = ",".join(["20262", "11740700", "둔촌2동", "129", "5", "4", "1", "", "17", "2", "1", "2",
                    "1", "", "", "", "", "", "", "", "", "1", "32"])
    path = _cp949_csv(tmp_path, "facility.csv", FACILITY_HEADER, row)
    by_type = {
        entity.facility_type: entity.facility_count
        for entity in SeoulFacilityCsvGateway().fetch_facilities(path)
    }
    assert by_type["hospital"] is None  # 일반_병원_수 공란
    assert by_type["theater"] is None
    assert by_type["subway_station"] == 1
    assert by_type["total"] == 129


# ---------- 지출: `음식`이 `기타` 뒤에 오는 함정 ----------


def test_spending_maps_etc_and_food_by_name_not_position(tmp_path):
    """**원천에서 `음식_지출_총금액`이 `기타_지출_총금액` 뒤에 온다.**

    순서로 매핑하면 `etc`와 `food` 두 항목이 통째로 뒤바뀐다. 음식 지출은 상권 분석의 핵심
    항목이라 뒤바뀌면 결론이 반대가 된다.
    """
    # 실 원천 1행 (둔촌2동 2026Q2) — 마지막 두 값이 기타 311,389,000 · 음식 1,128,140,000이다
    row = (
        "20262,11740700,둔촌2동,4163793000,715793000,67915000,170569000,468642000,809402000,"
        "158175000,32211000,301557000,311389000,1128140000"
    )
    path = _cp949_csv(tmp_path, "spending.csv", SPENDING_HEADER, row)

    rows = list(SeoulSpendingCsvGateway().fetch_spending(path))
    assert len(rows) == 11
    by_category = {entity.spending_category: entity.amount for entity in rows}
    assert by_category["etc"] == 311389000  # 뒤에서 두 번째 컬럼
    assert by_category["food"] == 1128140000  # 마지막 컬럼 — 순서로 짜면 여기가 etc가 된다
    assert by_category["total"] == 4163793000
    assert by_category["grocery"] == 715793000
    assert by_category["leisure_culture"] == 301557000

    # 헤더 순서 자체가 사전순도 논리순도 아님을 고정한다
    header_columns = SPENDING_HEADER.split(",")
    assert header_columns.index("기타_지출_총금액") < header_columns.index("음식_지출_총금액")


def test_spending_column_names_match_the_source_header_exactly():
    """매핑 표의 컬럼명이 실 헤더와 한 글자도 다르지 않아야 한다."""
    header_columns = set(SPENDING_HEADER.split(","))
    assert {column for _, column in SPENDING_COLUMNS} <= header_columns


# ---------- 상권변화지표 + 서울 평균 2NF 분리 ----------


def _change_row(quarter: str, adstrd: str, seoul_operating: str, seoul_closed: str) -> str:
    return f"{quarter},{adstrd},동이름,HL,상권축소,126,52,{seoul_operating},{seoul_closed}"


def test_change_keeps_categorical_code_and_name(tmp_path):
    path = _cp949_csv(
        tmp_path, "change.csv", CHANGE_HEADER, _change_row("20262", "11740700", "118", "54")
    )
    rows = list(SeoulCommerceChangeCsvGateway().fetch_changes(path))
    assert len(rows) == 1
    assert (rows[0].change_code, rows[0].change_name) == ("HL", "상권축소")
    assert (rows[0].operating_months, rows[0].closed_months) == (126.0, 52.0)
    assert rows[0].year_quarter == "20262"


def test_seoul_baseline_is_deduplicated_per_quarter(tmp_path):
    """서울 평균은 분기에만 의존한다 — 425개 동 행이 분기당 1행으로 줄어야 한다(§3-5)."""
    path = _cp949_csv(
        tmp_path,
        "change.csv",
        CHANGE_HEADER,
        _change_row("20262", "11740700", "118", "54"),
        _change_row("20262", "11110515", "118", "54"),
        _change_row("20261", "11740700", "117", "53"),
        _change_row("20261", "11110515", "117", "53"),
    )
    rows = list(SeoulCommerceChangeBaselineCsvGateway().fetch_baselines(path))
    assert [(row.year_quarter, row.seoul_operating_months) for row in rows] == [
        ("20262", 118.0),
        ("20261", 117.0),
    ]


# ---------- region 해석 ----------


class _FakeRegionCatalog(RegionCatalogPort):
    def region_code_by_adstrd(self) -> dict[str, str]:
        return {"11110515": "1111051500"}


class _FakeGateway:
    def __init__(self, rows):
        self._rows = rows

    def fetch_footfall(self, path):
        return iter(self._rows)


class _RecordingRepository:
    def __init__(self):
        self.rows = []

    def upsert(self, rows):
        self.rows.extend(rows)
        return len(rows)


def _footfall(adstrd_code: str, dim_key: str = "all") -> RegionFootfallQuarter:
    return RegionFootfallQuarter(
        adstrd_code=adstrd_code,
        year_quarter="20251",
        dim_type="total",
        dim_key=dim_key,
        region_code=None,
        headcount=10,
    )


def test_ingest_resolves_8digit_prefix_and_keeps_unmatched_rows():
    """원천에만 있는 옛 행정동(용신동 11230536)은 버리지 않고 region_code NULL로 적재한다."""
    repository = _RecordingRepository()
    interactor = RegionFootfallQuarterIngestInteractor(
        repository=repository,
        gateway=_FakeGateway([_footfall("11110515"), _footfall("11230536")]),
        region_catalog=_FakeRegionCatalog(),
    )
    result = interactor.ingest([Path("unused.csv")])
    assert result.processed == 2
    assert (result.region_resolved, result.region_unresolved) == (1, 1)
    assert [row.region_code for row in repository.rows] == ["1111051500", None]


def test_ingest_streams_in_chunks(monkeypatch):
    """긴 형태 106만 행을 한 리스트로 들지 않는다 — 청크마다 업서트가 끊겨야 한다."""
    monkeypatch.setattr(
        "apps.neighborhood.app.use_cases.region_quarter_ingest.CHUNK_SIZE", 3
    )

    class _CountingRepository(_RecordingRepository):
        def __init__(self):
            super().__init__()
            self.calls = []

        def upsert(self, rows):
            self.calls.append(len(rows))
            return super().upsert(rows)

    repository = _CountingRepository()
    rows = [_footfall("11110515", dim_key=f"k{index}") for index in range(7)]
    interactor = RegionFootfallQuarterIngestInteractor(
        repository=repository,
        gateway=_FakeGateway(rows),
        region_catalog=_FakeRegionCatalog(),
    )
    assert interactor.ingest([Path("unused.csv")]).processed == 7
    assert repository.calls == [3, 3, 1]


# ---------- 멱등 업서트 + FK 순서 (실 DB) ----------


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(RegionFootfallQuarterOrm).where(
                RegionFootfallQuarterOrm.adstrd_code == _TEST_ADSTRD
            )
        )
        session.execute(
            delete(RegionCommerceChangeOrm).where(
                RegionCommerceChangeOrm.adstrd_code == _TEST_ADSTRD
            )
        )
        session.execute(
            delete(SeoulCommerceChangeBaselineOrm).where(
                SeoulCommerceChangeBaselineOrm.year_quarter == _TEST_QUARTER
            )
        )


def test_footfall_upsert_is_idempotent_and_updates_values():
    _cleanup()
    repository = SqlAlchemyRegionFootfallQuarterRepository()

    def entity(headcount: int) -> RegionFootfallQuarter:
        return RegionFootfallQuarter(
            adstrd_code=_TEST_ADSTRD,
            year_quarter=_TEST_QUARTER,
            dim_type="hour",
            dim_key="00_06",
            region_code=None,
            headcount=headcount,
        )

    assert repository.upsert([entity(10)]) == 1
    assert repository.upsert([entity(20)]) == 1
    with session_scope() as session:
        rows = (
            session.execute(
                select(RegionFootfallQuarterOrm).where(
                    RegionFootfallQuarterOrm.adstrd_code == _TEST_ADSTRD
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].headcount == 20
    _cleanup()


def test_change_requires_baseline_row_first():
    """서울 평균이 없는 분기의 동별 행은 DB가 막는다 — 적재 순서가 baseline 먼저인 이유."""
    _cleanup()
    change = RegionCommerceChange(
        adstrd_code=_TEST_ADSTRD,
        year_quarter=_TEST_QUARTER,
        change_code="LL",
        change_name="다이나믹",
        operating_months=100.0,
        closed_months=50.0,
        region_code=None,
    )
    try:
        SqlAlchemyRegionCommerceChangeRepository().upsert([change])
    except Exception as error:  # psycopg ForeignKeyViolation
        assert "seoul_commerce_change_baseline" in str(error)
    else:
        raise AssertionError("baseline 없이 동별 변화 행이 들어가면 안 된다")

    SqlAlchemySeoulCommerceChangeBaselineRepository().upsert(
        [
            SeoulCommerceChangeBaseline(
                year_quarter=_TEST_QUARTER,
                seoul_operating_months=111.0,
                seoul_closed_months=52.0,
            )
        ]
    )
    assert SqlAlchemyRegionCommerceChangeRepository().upsert([change]) == 1
    assert SqlAlchemyRegionCommerceChangeRepository().upsert([change]) == 1
    with session_scope() as session:
        count = session.execute(
            select(func.count())
            .select_from(RegionCommerceChangeOrm)
            .where(RegionCommerceChangeOrm.adstrd_code == _TEST_ADSTRD)
        ).scalar_one()
    assert count == 1
    _cleanup()


def test_full_wiring_ingests_real_layout_csv_idempotently(tmp_path):
    """게이트웨이→인터랙터→리포지토리 전 배선을 두 번 태워도 행 수가 변하지 않는다."""
    _cleanup()
    row = ",".join([_TEST_QUARTER, _TEST_ADSTRD, "테스트동", *[str(100 + i) for i in range(22)]])
    path = _cp949_csv(tmp_path, "footfall.csv", FOOTFALL_HEADER, row)
    interactor = RegionFootfallQuarterIngestInteractor(
        repository=SqlAlchemyRegionFootfallQuarterRepository(),
        gateway=SeoulFootfallCsvGateway(),
        region_catalog=_FakeRegionCatalog(),
    )
    assert interactor.ingest([path]).processed == 22
    assert interactor.ingest([path]).processed == 22
    with session_scope() as session:
        count = session.execute(
            select(func.count())
            .select_from(RegionFootfallQuarterOrm)
            .where(RegionFootfallQuarterOrm.adstrd_code == _TEST_ADSTRD)
        ).scalar_one()
    assert count == 22
    _cleanup()
