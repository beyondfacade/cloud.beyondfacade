"""서울 상권분석서비스 행정동 CSV Driven Adapter — 원천이 외부 API가 아니라 로컬 파일이다.

실데이터 실측 사실 (설계서 §2, 2026-09-23 확보분):
- 인코딩 CP949. UTF-8로 읽으면 첫 줄부터 깨진다
- 연도 컬럼은 `기준_년_코드`가 아니라 `기준_년분기_코드`, 값은 '20251'(2025년 1분기) 5자리다.
  정수로 바꾸면 2025년과 구분되지 않으므로 문자열로 보존한다
- 헤더에 오타가 있다. 시간대 건수 6종이 `시간대_건수~06_매출_건수` 형태다. 그래서 분해 47컬럼은
  이름이 아니라 헤더 순서로 잡는다 (`breakdown_columns`)
- 점포 쪽 표기는 `개업_율` / `폐업_률`로 비대칭이다. 오타가 아니라 원천 그대로다
- 결측은 0으로 채우지 않고 None으로 보존한다
"""

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from apps.commerce.app.ports.output.region_commerce_sales_breakdown_port import (
    RegionCommerceSalesBreakdownGatewayPort,
)
from apps.commerce.app.ports.output.region_commerce_sales_port import (
    RegionCommerceSalesGatewayPort,
)
from apps.commerce.app.ports.output.region_commerce_store_port import (
    RegionCommerceStoreGatewayPort,
)
from apps.commerce.domain.entities.region_commerce_sales_breakdown_entity import (
    RegionCommerceSalesBreakdown,
)
from apps.commerce.domain.entities.region_commerce_sales_entity import RegionCommerceSales
from apps.commerce.domain.entities.region_commerce_store_entity import RegionCommerceStore

ENCODING = "cp949"
YEAR_QUARTER_COLUMN = "기준_년분기_코드"


def _text(row: dict[str, str], column: str) -> str:
    return (row.get(column) or "").strip()


def _int(row: dict[str, str], column: str) -> int | None:
    value = _text(row, column)
    return int(float(value)) if value else None


def _float(row: dict[str, str], column: str) -> float | None:
    value = _text(row, column)
    return float(value) if value else None


def read_rows(path: Path) -> Iterator[dict[str, str]]:
    with open(path, encoding=ENCODING, newline="") as f:
        yield from csv.DictReader(f)


def parse_sales_row(row: dict[str, str]) -> RegionCommerceSales:
    """CSV 1행 → 추정매출 엔티티. region_code는 인터랙터가 채운다."""
    return RegionCommerceSales(
        adstrd_code=_text(row, "행정동_코드"),
        service_industry_code=_text(row, "서비스_업종_코드"),
        year_quarter=_text(row, YEAR_QUARTER_COLUMN),
        region_code=None,
        sales_amount=_int(row, "당월_매출_금액"),
        sales_count=_int(row, "당월_매출_건수"),
    )


def parse_store_row(row: dict[str, str]) -> RegionCommerceStore:
    """CSV 1행 → 점포 엔티티. 개업은 '율', 폐업은 '률' — 원천 표기 그대로 읽는다."""
    return RegionCommerceStore(
        adstrd_code=_text(row, "행정동_코드"),
        service_industry_code=_text(row, "서비스_업종_코드"),
        year_quarter=_text(row, YEAR_QUARTER_COLUMN),
        region_code=None,
        store_count=_int(row, "점포_수"),
        similar_industry_store_count=_int(row, "유사_업종_점포_수"),
        open_rate=_float(row, "개업_율"),
        open_store_count=_int(row, "개업_점포_수"),
        close_rate=_float(row, "폐업_률"),
        close_store_count=_int(row, "폐업_점포_수"),
        franchise_store_count=_int(row, "프랜차이즈_점포_수"),
    )


class SeoulCommerceSalesCsvGateway(RegionCommerceSalesGatewayPort):
    def fetch_sales(self, path: Path) -> list[RegionCommerceSales]:
        return [parse_sales_row(row) for row in read_rows(path)]


class SeoulCommerceStoreCsvGateway(RegionCommerceStoreGatewayPort):
    def fetch_stores(self, path: Path) -> list[RegionCommerceStore]:
        return [parse_store_row(row) for row in read_rows(path)]


# ---------- 추정매출 분해 47컬럼 → 1NF long (설계서 §4-1) ----------

TOTAL_COUNT_COLUMN = "당월_매출_건수"  # 분해 블록 바로 앞 컬럼 — 블록 시작점의 기준

# 원천 헤더에 놓인 순서 그대로의 분해 구간 23종. 금액 23컬럼이 먼저 오고 같은 순서로
# 건수 23컬럼이 이어진다 (53컬럼 = 식별 5 + 총계 2 + 23 × 2).
BREAKDOWN_DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("weekpart", "weekday"),  # 주중
    ("weekpart", "weekend"),  # 주말
    ("dow", "mon"),
    ("dow", "tue"),
    ("dow", "wed"),
    ("dow", "thu"),
    ("dow", "fri"),
    ("dow", "sat"),
    ("dow", "sun"),
    ("hour", "00_06"),
    ("hour", "06_11"),
    ("hour", "11_14"),
    ("hour", "14_17"),
    ("hour", "17_21"),
    ("hour", "21_24"),
    ("gender", "male"),
    ("gender", "female"),
    ("age", "10"),
    ("age", "20"),
    ("age", "30"),
    ("age", "40"),
    ("age", "50"),
    ("age", "60_over"),  # 연령대_60_이상
)


@dataclass(frozen=True)
class BreakdownColumn:
    """구간 1개가 원천 헤더의 어느 자리에서 오는지 — 이름이 아니라 위치가 진실이다."""

    dim_type: str
    dim_key: str
    amount_index: int
    count_index: int
    amount_column: str  # 실제 헤더 문자열 (진단·테스트용)
    count_column: str  # 시간대 6종은 `시간대_건수~06_매출_건수` 오타가 그대로 들어온다


def breakdown_columns(header: list[str]) -> list[BreakdownColumn]:
    """헤더 순서로 구간 23개의 금액·건수 위치를 잡는다.

    이름으로 찾지 않는 근거: 원천 시간대 건수 6종의 헤더가 `시간대_00~06_매출_건수`가 아니라
    `시간대_건수~06_매출_건수`로 오타다(설계서 §2). 이름 기준으로 짜면 시간대 건수가 통째로
    누락되거나, 더 나쁘게는 엉뚱한 구간에 붙는다.
    """
    start = header.index(TOTAL_COUNT_COLUMN) + 1
    span = len(BREAKDOWN_DIMENSIONS)
    if len(header) != start + span * 2:
        raise ValueError(
            f"원천 헤더 레이아웃이 바뀌었다: 분해 컬럼 {span * 2}개 기대, {len(header) - start}개"
        )
    return [
        BreakdownColumn(
            dim_type=dim_type,
            dim_key=dim_key,
            amount_index=start + offset,
            count_index=start + span + offset,
            amount_column=header[start + offset],
            count_column=header[start + span + offset],
        )
        for offset, (dim_type, dim_key) in enumerate(BREAKDOWN_DIMENSIONS)
    ]


def _int_value(value: str) -> int | None:
    text = value.strip()
    return int(float(text)) if text else None


def read_breakdown_rows(path: Path) -> Iterator[RegionCommerceSalesBreakdown]:
    """CSV 1행 → 구간 23행. 789만 행이라 리스트로 모으지 않고 흘려보낸다."""
    with open(path, encoding=ENCODING, newline="") as f:
        reader = csv.reader(f)
        header = [column.strip() for column in next(reader)]
        columns = breakdown_columns(header)
        adstrd_index = header.index("행정동_코드")
        industry_index = header.index("서비스_업종_코드")
        quarter_index = header.index(YEAR_QUARTER_COLUMN)
        for values in reader:
            adstrd_code = values[adstrd_index].strip()
            service_industry_code = values[industry_index].strip()
            year_quarter = values[quarter_index].strip()
            for column in columns:
                yield RegionCommerceSalesBreakdown(
                    adstrd_code=adstrd_code,
                    service_industry_code=service_industry_code,
                    year_quarter=year_quarter,
                    dim_type=column.dim_type,
                    dim_key=column.dim_key,
                    region_code=None,
                    amount=_int_value(values[column.amount_index]),
                    count=_int_value(values[column.count_index]),
                )


class SeoulCommerceSalesBreakdownCsvGateway(RegionCommerceSalesBreakdownGatewayPort):
    def fetch_breakdown(self, path: Path) -> Iterator[RegionCommerceSalesBreakdown]:
        return read_breakdown_rows(path)
