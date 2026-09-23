"""서울 상권분석서비스 동네 맥락 7종 CSV Driven Adapter — 원천이 외부 API가 아니라 로컬 파일이다.

실데이터 실측 사실 (설계서 §2 · §3, 2026-09-23 확보분).

- 인코딩 **CP949**, 줄바꿈 **LF**. commerce의 ZIP 내 CSV는 CRLF였다 — `newline=""`가 둘 다 흡수한다
- 시점 컬럼은 `기준_년분기_코드`, 값은 `'20251'` 5자리. **정수 변환 금지** (연도와 구분 불가)
- 범위 20211~20262 **22분기**. commerce(20분기)보다 넓다. 자르지 않고 전량 적재하고,
  조인할 때 `year_quarter <= '20254'`로 자르는 것은 조회하는 쪽 몫이다
- **컬럼은 이름으로 찾는다.** 다만 데이터셋별 규칙이 다르다
  · 유동인구 시간대는 밑줄 `시간대_00_06_유동인구_수` (commerce 추정매출은 물결표 `00~06`)
  · 직장은 `_직장_인구_수`, 상주는 `_상주인구_수` — 접미사 모양이 다르다
  · **소비는 `음식_지출_총금액`이 `기타_지출_총금액` 뒤에 온다.** 순서로 매핑하면 두 항목이
    통째로 뒤바뀐다. 이 파일이 순서를 쓰지 않는 이유다
- 결측은 0으로 채우지 않고 None으로 보존한다

헤더에 기대한 이름이 없으면 조용히 NULL을 적재하는 대신 `ValueError`로 즉시 깨뜨린다 —
원천 컬럼명이 바뀌면 전개 행 수는 그대로인 채 값만 비는 사고가 가장 찾기 어렵다.
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from apps.neighborhood.app.ports.output.region_commerce_change_port import (
    RegionCommerceChangeGatewayPort,
)
from apps.neighborhood.app.ports.output.region_facility_quarter_port import (
    RegionFacilityQuarterGatewayPort,
)
from apps.neighborhood.app.ports.output.region_footfall_quarter_port import (
    RegionFootfallQuarterGatewayPort,
)
from apps.neighborhood.app.ports.output.region_household_quarter_port import (
    RegionHouseholdQuarterGatewayPort,
)
from apps.neighborhood.app.ports.output.region_housing_average_quarter_port import (
    RegionHousingAverageQuarterGatewayPort,
)
from apps.neighborhood.app.ports.output.region_population_quarter_port import (
    RegionPopulationQuarterGatewayPort,
)
from apps.neighborhood.app.ports.output.region_spending_quarter_port import (
    RegionSpendingQuarterGatewayPort,
)
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_port import (
    SeoulCommerceChangeBaselineGatewayPort,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import RegionCommerceChange
from apps.neighborhood.domain.entities.region_facility_quarter_entity import RegionFacilityQuarter
from apps.neighborhood.domain.entities.region_footfall_quarter_entity import RegionFootfallQuarter
from apps.neighborhood.domain.entities.region_household_quarter_entity import RegionHouseholdQuarter
from apps.neighborhood.domain.entities.region_housing_average_quarter_entity import (
    RegionHousingAverageQuarter,
)
from apps.neighborhood.domain.entities.region_population_quarter_entity import (
    RegionPopulationQuarter,
)
from apps.neighborhood.domain.entities.region_spending_quarter_entity import RegionSpendingQuarter
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)
from apps.neighborhood.domain.value_objects.quarter_dimension import (
    AGE_KEYS,
    DOW_KEYS,
    GENDER_KEYS,
    HOUR_KEYS,
)

ENCODING = "cp949"
YEAR_QUARTER_COLUMN = "기준_년분기_코드"
ADSTRD_COLUMN = "행정동_코드"


def _text(row: dict[str, str], column: str) -> str:
    return (row.get(column) or "").strip()


def _int(row: dict[str, str], column: str) -> int | None:
    value = _text(row, column)
    return int(float(value)) if value else None


def _float(row: dict[str, str], column: str) -> float | None:
    value = _text(row, column)
    return float(value) if value else None


def require_columns(header: list[str], columns: list[str], dataset: str) -> None:
    """기대한 컬럼이 헤더에 전부 있는지 확인한다. 없으면 값만 비는 대신 즉시 깨뜨린다."""
    missing = [column for column in columns if column not in header]
    if missing:
        raise ValueError(f"{dataset} 원천 헤더에 없는 컬럼: {missing}")


def read_rows(path: Path, dataset: str, columns: list[str]) -> Iterator[dict[str, str]]:
    with open(path, encoding=ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        require_columns(
            [name.strip() for name in (reader.fieldnames or [])],
            [ADSTRD_COLUMN, YEAR_QUARTER_COLUMN, *columns],
            dataset,
        )
        yield from reader


# ---------- 원천 구간 표기 ↔ 저장 dim_key (설계서 §5) ----------

# 연령대는 세 데이터셋이 같은 표기를 쓴다: 연령대_10 ~ 연령대_60_이상
_AGE_SOURCE = ("연령대_10", "연령대_20", "연령대_30", "연령대_40", "연령대_50", "연령대_60_이상")
# 유동인구 시간대는 **밑줄** 표기다 (commerce 추정매출은 물결표 `시간대_00~06`)
_HOUR_SOURCE = (
    "시간대_00_06",
    "시간대_06_11",
    "시간대_11_14",
    "시간대_14_17",
    "시간대_17_21",
    "시간대_21_24",
)
_DOW_SOURCE = ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")
_GENDER_SOURCE = ("남성", "여성")


# ---------- 유동인구 (OA-22178) — 원본 1행 → 22행 ----------

FOOTFALL_SUFFIX = "_유동인구_수"


def footfall_dimensions() -> list[tuple[str, str, str]]:
    """(dim_type, dim_key, 원천 컬럼명) 22구간. total 1 · gender 2 · age 6 · hour 6 · dow 7."""
    dimensions: list[tuple[str, str, str]] = [("total", "all", f"총{FOOTFALL_SUFFIX}")]
    for axis, keys, sources in (
        ("gender", GENDER_KEYS, _GENDER_SOURCE),
        ("age", AGE_KEYS, _AGE_SOURCE),
        ("hour", HOUR_KEYS, _HOUR_SOURCE),
        ("dow", DOW_KEYS, _DOW_SOURCE),
    ):
        dimensions += [
            (axis, key, f"{source}{FOOTFALL_SUFFIX}")
            for key, source in zip(keys, sources, strict=True)
        ]
    return dimensions


class SeoulFootfallCsvGateway(RegionFootfallQuarterGatewayPort):
    def fetch_footfall(self, path: Path) -> Iterator[RegionFootfallQuarter]:
        dimensions = footfall_dimensions()
        columns = [column for _, _, column in dimensions]
        for row in read_rows(path, "유동인구", columns):
            adstrd_code = _text(row, ADSTRD_COLUMN)
            year_quarter = _text(row, YEAR_QUARTER_COLUMN)
            for dim_type, dim_key, column in dimensions:
                yield RegionFootfallQuarter(
                    adstrd_code=adstrd_code,
                    year_quarter=year_quarter,
                    dim_type=dim_type,
                    dim_key=dim_key,
                    region_code=None,
                    headcount=_int(row, column),
                )


# ---------- 직장·상주인구 (OA-22184 · OA-22183) — 원본 1행 → 21행 ----------

# 접미사가 데이터셋마다 다르다. 직장은 `_직장_인구_수`, 상주는 `_상주인구_수` — 값 컬럼 21개의
# 축 구성은 한 글자도 다르지 않다(설계서 §3-3).
WORKER_SUFFIX = "_직장_인구_수"
RESIDENT_SUFFIX = "_상주인구_수"


def population_dimensions(suffix: str) -> list[tuple[str, str, str]]:
    """total 1 · gender 2 · age 6 · gender_age 12 = 21구간."""
    dimensions: list[tuple[str, str, str]] = [("total", "all", f"총{suffix}")]
    dimensions += [
        ("gender", key, f"{source}{suffix}")
        for key, source in zip(GENDER_KEYS, _GENDER_SOURCE, strict=True)
    ]
    dimensions += [
        ("age", key, f"{source}{suffix}")
        for key, source in zip(AGE_KEYS, _AGE_SOURCE, strict=True)
    ]
    for gender_key, gender_source in zip(GENDER_KEYS, _GENDER_SOURCE, strict=True):
        dimensions += [
            ("gender_age", f"{gender_key}_{age_key}", f"{gender_source}{age_source}{suffix}")
            for age_key, age_source in zip(AGE_KEYS, _AGE_SOURCE, strict=True)
        ]
    return dimensions


class _PopulationCsvGateway(RegionPopulationQuarterGatewayPort):
    """직장·상주 공통 파서 — 한 포트, 두 어댑터 (population_type과 접미사만 다르다)."""

    population_type: str
    suffix: str
    dataset: str

    def fetch_population(self, path: Path) -> Iterator[RegionPopulationQuarter]:
        dimensions = population_dimensions(self.suffix)
        columns = [column for _, _, column in dimensions]
        for row in read_rows(path, self.dataset, columns):
            adstrd_code = _text(row, ADSTRD_COLUMN)
            year_quarter = _text(row, YEAR_QUARTER_COLUMN)
            for dim_type, dim_key, column in dimensions:
                yield RegionPopulationQuarter(
                    adstrd_code=adstrd_code,
                    year_quarter=year_quarter,
                    population_type=self.population_type,
                    dim_type=dim_type,
                    dim_key=dim_key,
                    region_code=None,
                    headcount=_int(row, column),
                )


class SeoulWorkerPopulationCsvGateway(_PopulationCsvGateway):
    """직장인구 — **414개 동뿐이다**(11개 부족). 없는 동의 행을 만들지 않는다(설계서 §3-2)."""

    population_type = "worker"
    suffix = WORKER_SUFFIX
    dataset = "직장인구"


class SeoulResidentPopulationCsvGateway(_PopulationCsvGateway):
    population_type = "resident"
    suffix = RESIDENT_SUFFIX
    dataset = "상주인구"


# ---------- 가구·아파트 (설계서 §4-3) ----------

# 상주인구 원천의 가구 3종 — 인구가 아니라 주거 스톡이라 인구 테이블이 아니라 이쪽으로 보낸다
HOUSEHOLD_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("household", "total", "총_가구_수"),
    ("household", "apartment", "아파트_가구_수"),
    ("household", "non_apartment", "비_아파트_가구_수"),
)

# 아파트 원천 13종. 면적은 `66_제곱미터_미만`/`66_제곱미터`, 가격은 `1_억_미만`/`1_억`/`6_억_이상`
APARTMENT_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("apartment_complex", "count", "아파트_단지_수"),
    ("apartment_area", "under_66", "아파트_면적_66_제곱미터_미만_세대_수"),
    ("apartment_area", "66", "아파트_면적_66_제곱미터_세대_수"),
    ("apartment_area", "99", "아파트_면적_99_제곱미터_세대_수"),
    ("apartment_area", "132", "아파트_면적_132_제곱미터_세대_수"),
    ("apartment_area", "165", "아파트_면적_165_제곱미터_세대_수"),
    ("apartment_price", "under_100m", "아파트_가격_1_억_미만_세대_수"),
    ("apartment_price", "100m", "아파트_가격_1_억_세대_수"),
    ("apartment_price", "200m", "아파트_가격_2_억_세대_수"),
    ("apartment_price", "300m", "아파트_가격_3_억_세대_수"),
    ("apartment_price", "400m", "아파트_가격_4_억_세대_수"),
    ("apartment_price", "500m", "아파트_가격_5_억_세대_수"),
    ("apartment_price", "over_600m", "아파트_가격_6_억_이상_세대_수"),
)

AVG_AREA_COLUMN = "아파트_평균_면적"
AVG_PRICE_COLUMN = "아파트_평균_시가"


class _HouseholdCsvGateway(RegionHouseholdQuarterGatewayPort):
    """한 포트, 두 어댑터 — 상주인구 CSV와 아파트 CSV가 같은 테이블에 다른 dim_type을 넣는다."""

    dimensions: tuple[tuple[str, str, str], ...]
    dataset: str

    def fetch_households(self, path: Path) -> Iterator[RegionHouseholdQuarter]:
        columns = [column for _, _, column in self.dimensions]
        for row in read_rows(path, self.dataset, columns):
            adstrd_code = _text(row, ADSTRD_COLUMN)
            year_quarter = _text(row, YEAR_QUARTER_COLUMN)
            for dim_type, dim_key, column in self.dimensions:
                yield RegionHouseholdQuarter(
                    adstrd_code=adstrd_code,
                    year_quarter=year_quarter,
                    dim_type=dim_type,
                    dim_key=dim_key,
                    region_code=None,
                    value=_int(row, column),
                )


class SeoulResidentHouseholdCsvGateway(_HouseholdCsvGateway):
    dimensions = HOUSEHOLD_DIMENSIONS
    dataset = "상주인구(가구)"


class SeoulApartmentHouseholdCsvGateway(_HouseholdCsvGateway):
    """아파트는 `11740690`(둔촌1동)이 20211~20213 3분기만 있다 — 정상이다(설계서 §3-2)."""

    dimensions = APARTMENT_DIMENSIONS
    dataset = "아파트"


class SeoulHousingAverageCsvGateway(RegionHousingAverageQuarterGatewayPort):
    def fetch_housing_averages(self, path: Path) -> Iterator[RegionHousingAverageQuarter]:
        for row in read_rows(path, "아파트(평균)", [AVG_AREA_COLUMN, AVG_PRICE_COLUMN]):
            yield RegionHousingAverageQuarter(
                adstrd_code=_text(row, ADSTRD_COLUMN),
                year_quarter=_text(row, YEAR_QUARTER_COLUMN),
                region_code=None,
                avg_area_m2=_float(row, AVG_AREA_COLUMN),
                avg_price=_int(row, AVG_PRICE_COLUMN),
            )


# ---------- 집객시설 (OA-22169) — 원본 1행 → total + 19종 = 20행 ----------

FACILITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("total", "집객시설_수"),
    ("government", "관공서_수"),
    ("bank", "은행_수"),
    ("general_hospital", "종합병원_수"),
    ("hospital", "일반_병원_수"),
    ("pharmacy", "약국_수"),
    ("kindergarten", "유치원_수"),
    ("elementary_school", "초등학교_수"),
    ("middle_school", "중학교_수"),
    ("high_school", "고등학교_수"),
    ("university", "대학교_수"),
    ("department_store", "백화점_수"),
    ("supermarket", "슈퍼마켓_수"),
    ("theater", "극장_수"),
    ("lodging", "숙박_시설_수"),
    ("airport", "공항_수"),
    ("train_station", "철도_역_수"),
    ("bus_terminal", "버스_터미널_수"),
    ("subway_station", "지하철_역_수"),
    ("bus_stop", "버스_정거장_수"),
)


class SeoulFacilityCsvGateway(RegionFacilityQuarterGatewayPort):
    def fetch_facilities(self, path: Path) -> Iterator[RegionFacilityQuarter]:
        columns = [column for _, column in FACILITY_COLUMNS]
        for row in read_rows(path, "집객시설", columns):
            adstrd_code = _text(row, ADSTRD_COLUMN)
            year_quarter = _text(row, YEAR_QUARTER_COLUMN)
            for facility_type, column in FACILITY_COLUMNS:
                yield RegionFacilityQuarter(
                    adstrd_code=adstrd_code,
                    year_quarter=year_quarter,
                    facility_type=facility_type,
                    region_code=None,
                    facility_count=_int(row, column),
                )


# ---------- 지출 (OA-22166) — 원본 1행 → total + 10종 = 11행 ----------

# **`음식`이 `기타` 뒤에 온다.** 여기 나열 순서는 원천 헤더 순서를 그대로 옮긴 것이고,
# 매핑은 순서가 아니라 컬럼명으로 이뤄진다. 순서로 짜면 `etc`와 `food`가 뒤바뀐다(설계서 §3-7).
SPENDING_COLUMNS: tuple[tuple[str, str], ...] = (
    ("total", "지출_총금액"),
    ("grocery", "식료품_지출_총금액"),
    ("clothing_shoes", "의류_신발_지출_총금액"),
    ("household_goods", "생활용품_지출_총금액"),
    ("medical", "의료비_지출_총금액"),
    ("transport", "교통_지출_총금액"),
    ("education", "교육_지출_총금액"),
    ("entertainment", "유흥_지출_총금액"),
    ("leisure_culture", "여가_문화_지출_총금액"),
    ("etc", "기타_지출_총금액"),
    ("food", "음식_지출_총금액"),
)


class SeoulSpendingCsvGateway(RegionSpendingQuarterGatewayPort):
    def fetch_spending(self, path: Path) -> Iterator[RegionSpendingQuarter]:
        columns = [column for _, column in SPENDING_COLUMNS]
        for row in read_rows(path, "소비", columns):
            adstrd_code = _text(row, ADSTRD_COLUMN)
            year_quarter = _text(row, YEAR_QUARTER_COLUMN)
            for spending_category, column in SPENDING_COLUMNS:
                yield RegionSpendingQuarter(
                    adstrd_code=adstrd_code,
                    year_quarter=year_quarter,
                    spending_category=spending_category,
                    region_code=None,
                    amount=_int(row, column),
                )


# ---------- 상권변화지표 (OA-15575) ----------

CHANGE_CODE_COLUMN = "상권_변화_지표"
CHANGE_NAME_COLUMN = "상권_변화_지표_명"
OPERATING_MONTHS_COLUMN = "운영_영업_개월_평균"
CLOSED_MONTHS_COLUMN = "폐업_영업_개월_평균"
SEOUL_OPERATING_MONTHS_COLUMN = "서울_운영_영업_개월_평균"
SEOUL_CLOSED_MONTHS_COLUMN = "서울_폐업_영업_개월_평균"


class SeoulCommerceChangeCsvGateway(RegionCommerceChangeGatewayPort):
    def fetch_changes(self, path: Path) -> Iterator[RegionCommerceChange]:
        columns = [
            CHANGE_CODE_COLUMN,
            CHANGE_NAME_COLUMN,
            OPERATING_MONTHS_COLUMN,
            CLOSED_MONTHS_COLUMN,
        ]
        for row in read_rows(path, "상권변화지표", columns):
            yield RegionCommerceChange(
                adstrd_code=_text(row, ADSTRD_COLUMN),
                year_quarter=_text(row, YEAR_QUARTER_COLUMN),
                change_code=_text(row, CHANGE_CODE_COLUMN) or None,
                change_name=_text(row, CHANGE_NAME_COLUMN) or None,
                operating_months=_float(row, OPERATING_MONTHS_COLUMN),
                closed_months=_float(row, CLOSED_MONTHS_COLUMN),
                region_code=None,
            )


class SeoulCommerceChangeBaselineCsvGateway(SeoulCommerceChangeBaselineGatewayPort):
    """같은 CSV에서 분기별 서울 평균만 뽑아 중복을 제거한다 — 9,350행 → 22행 (설계서 §3-5).

    원천이 425개 동 행마다 같은 값을 반복해 싣는다. 분기당 고유값이 하나임은 실측으로 확인했고,
    여기서는 분기별 첫 등장을 취한다.
    """

    def fetch_baselines(self, path: Path) -> Iterator[SeoulCommerceChangeBaseline]:
        columns = [SEOUL_OPERATING_MONTHS_COLUMN, SEOUL_CLOSED_MONTHS_COLUMN]
        seen: set[str] = set()
        for row in read_rows(path, "상권변화지표(서울 평균)", columns):
            year_quarter = _text(row, YEAR_QUARTER_COLUMN)
            if year_quarter in seen:
                continue
            seen.add(year_quarter)
            yield SeoulCommerceChangeBaseline(
                year_quarter=year_quarter,
                seoul_operating_months=_float(row, SEOUL_OPERATING_MONTHS_COLUMN),
                seoul_closed_months=_float(row, SEOUL_CLOSED_MONTHS_COLUMN),
            )
