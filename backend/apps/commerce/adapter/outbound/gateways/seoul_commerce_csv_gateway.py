"""서울 상권분석서비스 행정동 CSV Driven Adapter — 원천이 외부 API가 아니라 로컬 파일이다.

실데이터 실측 사실 (설계서 §2, 2026-09-23 확보분):
- 인코딩 CP949. UTF-8로 읽으면 첫 줄부터 깨진다
- 연도 컬럼은 `기준_년_코드`가 아니라 `기준_년분기_코드`, 값은 '20251'(2025년 1분기) 5자리다.
  정수로 바꾸면 2025년과 구분되지 않으므로 문자열로 보존한다
- 헤더에 오타가 있다. 시간대 건수 6종이 `시간대_건수~06_매출_건수` 형태다. 이번 범위에서 쓰는
  컬럼은 아니지만, 분해 컬럼을 이름으로 찾는 코드는 반드시 순서 기준으로 짜야 한다
- 점포 쪽 표기는 `개업_율` / `폐업_률`로 비대칭이다. 오타가 아니라 원천 그대로다
- 결측은 0으로 채우지 않고 None으로 보존한다
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from apps.commerce.app.ports.output.region_commerce_sales_port import (
    RegionCommerceSalesGatewayPort,
)
from apps.commerce.app.ports.output.region_commerce_store_port import (
    RegionCommerceStoreGatewayPort,
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
