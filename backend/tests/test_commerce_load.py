"""commerce 적재 검증 — CSV 파싱(순수) + region 해석(순수) + 실 DB 멱등 업서트 (tobacco 전례).

실데이터 실측 사실을 고정한다: CP949 인코딩, `기준_년분기_코드` 5자리 문자열,
`개업_율`/`폐업_률` 비대칭 표기, 원천에만 있는 옛 행정동 3개의 region_code NULL 보존.
"""

from pathlib import Path

from sqlalchemy import delete, func, select

from apps.commerce.adapter.outbound.gateways.seoul_commerce_csv_gateway import (
    SeoulCommerceSalesCsvGateway,
    SeoulCommerceStoreCsvGateway,
    parse_sales_row,
    parse_store_row,
)
from apps.commerce.adapter.outbound.orms.region_commerce_sales_orm import RegionCommerceSalesOrm
from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.commerce.adapter.outbound.repositories.region_commerce_sales_repository import (
    SqlAlchemyRegionCommerceSalesRepository,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_store_repository import (
    SqlAlchemyRegionCommerceStoreRepository,
)
from apps.commerce.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.commerce.app.use_cases.region_commerce_sales_interactor import (
    RegionCommerceSalesIngestInteractor,
)
from apps.commerce.app.use_cases.region_commerce_store_interactor import (
    RegionCommerceStoreIngestInteractor,
)
from apps.commerce.domain.entities.region_commerce_sales_entity import RegionCommerceSales
from core.matrix.grid_oracle_database_manager import session_scope

# 실데이터와 충돌하지 않는 시험용 키 (원천 행정동_코드는 8자리 숫자, 업종은 CS로 시작)
_TEST_ADSTRD = "99999999"
_TEST_INDUSTRY = "TS900001"

# 실CSV(서울시 상권분석서비스(추정매출-행정동)_2024년.csv, 2026-09-23 확보) 헤더 실측 사본.
# 시간대 건수 6종의 오타(`시간대_건수~06_매출_건수`)를 그대로 옮겼다 — 원천 그대로임을 고정한다.
_SALES_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,서비스_업종_코드,서비스_업종_코드_명,"
    "당월_매출_금액,당월_매출_건수,주중_매출_금액,주말_매출_금액,"
    "시간대_00~06_매출_금액,시간대_건수~06_매출_건수"
)
_SALES_ROW = "20251,11110515,청운효자동,CS100010,커피-음료,3282036149,102492,2359720647,922315502,1316988,20"

_STORE_HEADER = (
    "기준_년분기_코드,행정동_코드,행정동_코드_명,서비스_업종_코드,서비스_업종_코드_명,"
    "점포_수,유사_업종_점포_수,개업_율,개업_점포_수,폐업_률,폐업_점포_수,프랜차이즈_점포_수"
)
_STORE_ROW = "20231,11110515,청운효자동,CS100001,한식음식점,74,75,4,3,4.5,3,1"


def _cp949_csv(tmp_path: Path, name: str, header: str, *rows: str) -> Path:
    path = tmp_path / name
    path.write_text("\n".join([header, *rows]) + "\n", encoding="cp949")
    return path


# ---------- CSV 파서 ----------


def test_sales_gateway_reads_cp949_and_keeps_year_quarter_as_text(tmp_path):
    path = _cp949_csv(tmp_path, "sales.csv", _SALES_HEADER, _SALES_ROW)
    (row,) = SeoulCommerceSalesCsvGateway().fetch_sales(path)
    assert row.adstrd_code == "11110515"
    assert row.service_industry_code == "CS100010"
    assert row.year_quarter == "20251"  # 정수 20251이 아니라 5자리 문자열
    assert row.sales_amount == 3282036149
    assert row.sales_count == 102492
    assert row.region_code is None  # 해석은 인터랙터 몫


def test_store_gateway_reads_asymmetric_open_close_rate_columns(tmp_path):
    """원천 표기가 개업은 '율', 폐업은 '률'로 비대칭이다 — 오타가 아니라 원천 그대로."""
    path = _cp949_csv(tmp_path, "store.csv", _STORE_HEADER, _STORE_ROW)
    (row,) = SeoulCommerceStoreCsvGateway().fetch_stores(path)
    assert row.year_quarter == "20231"
    assert row.store_count == 74
    assert row.similar_industry_store_count == 75
    assert row.open_rate == 4.0
    assert row.open_store_count == 3
    assert row.close_rate == 4.5
    assert row.close_store_count == 3
    assert row.franchise_store_count == 1


def test_blank_measures_stay_null_not_zero():
    """결측을 0으로 채우면 '매출 0원'과 '측정 없음'이 구분되지 않는다 (childcare EW_CNT_TOT 전례)."""
    row = parse_sales_row(
        {
            "기준_년분기_코드": "20251",
            "행정동_코드": "11110515",
            "서비스_업종_코드": "CS100010",
            "당월_매출_금액": "",
            "당월_매출_건수": "   ",
        }
    )
    assert row.sales_amount is None and row.sales_count is None

    store = parse_store_row(
        {
            "기준_년분기_코드": "20251",
            "행정동_코드": "11110515",
            "서비스_업종_코드": "CS100010",
            "점포_수": "",
            "유사_업종_점포_수": "",
            "개업_율": "",
            "개업_점포_수": "",
            "폐업_률": "",
            "폐업_점포_수": "",
            "프랜차이즈_점포_수": "",
        }
    )
    assert store.store_count is None and store.open_rate is None and store.close_rate is None


# ---------- region 해석 ----------


class _FakeRegionCatalog(RegionCatalogPort):
    def region_code_by_adstrd(self) -> dict[str, str]:
        return {"11110515": "1111051500"}


class _FakeSalesGateway:
    def __init__(self, rows):
        self._rows = rows

    def fetch_sales(self, path):
        return self._rows


class _RecordingRepository:
    def __init__(self):
        self.rows = []

    def upsert(self, rows):
        self.rows.extend(rows)
        return len(rows)


def _sales(adstrd_code: str) -> RegionCommerceSales:
    return RegionCommerceSales(
        adstrd_code=adstrd_code,
        service_industry_code="CS100010",
        year_quarter="20251",
        region_code=None,
        sales_amount=100,
        sales_count=2,
    )


def test_ingest_resolves_8digit_prefix_and_keeps_unmatched_rows():
    """원천에만 있는 옛 행정동(용신동 11230536)은 버리지 않고 region_code NULL로 적재한다."""
    repository = _RecordingRepository()
    interactor = RegionCommerceSalesIngestInteractor(
        repository=repository,
        gateway=_FakeSalesGateway([_sales("11110515"), _sales("11230536")]),
        region_catalog=_FakeRegionCatalog(),
    )
    result = interactor.ingest([Path("unused.csv")])
    assert result.processed == 2
    assert (result.region_resolved, result.region_unresolved) == (1, 1)
    assert [r.region_code for r in repository.rows] == ["1111051500", None]


# ---------- 멱등 업서트 (실 DB) ----------


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(RegionCommerceSalesOrm).where(
                RegionCommerceSalesOrm.adstrd_code == _TEST_ADSTRD
            )
        )
        session.execute(
            delete(RegionCommerceStoreOrm).where(
                RegionCommerceStoreOrm.adstrd_code == _TEST_ADSTRD
            )
        )


def _sales_entity(amount: int, region_code: str | None = None) -> RegionCommerceSales:
    return RegionCommerceSales(
        adstrd_code=_TEST_ADSTRD,
        service_industry_code=_TEST_INDUSTRY,
        year_quarter="20251",
        region_code=region_code,
        sales_amount=amount,
        sales_count=2,
    )


def test_sales_upsert_is_idempotent_and_updates_values():
    _cleanup()
    repository = SqlAlchemyRegionCommerceSalesRepository()
    assert repository.upsert([_sales_entity(100)]) == 1
    assert repository.upsert([_sales_entity(200)]) == 1
    with session_scope() as session:
        rows = session.execute(
            select(RegionCommerceSalesOrm).where(
                RegionCommerceSalesOrm.adstrd_code == _TEST_ADSTRD
            )
        ).scalars().all()
    assert len(rows) == 1  # 같은 PK 재적재로 행이 늘지 않는다
    assert rows[0].sales_amount == 200  # 값은 최신으로 갱신
    assert rows[0].region_code is None
    _cleanup()


def test_store_ingest_is_idempotent_through_interactor(tmp_path):
    """게이트웨이→인터랙터→리포지토리 전 배선을 같은 파일로 두 번 태워도 행 수가 변하지 않는다."""
    _cleanup()
    path = _cp949_csv(
        tmp_path,
        "store.csv",
        _STORE_HEADER,
        f"20251,{_TEST_ADSTRD},시험동,{_TEST_INDUSTRY},시험업종,74,75,4,3,4.5,3,1",
    )
    interactor = RegionCommerceStoreIngestInteractor(
        repository=SqlAlchemyRegionCommerceStoreRepository(),
        gateway=SeoulCommerceStoreCsvGateway(),
        region_catalog=_FakeRegionCatalog(),
    )
    assert interactor.ingest([path]).processed == 1
    assert interactor.ingest([path]).processed == 1
    with session_scope() as session:
        count = session.execute(
            select(func.count())
            .select_from(RegionCommerceStoreOrm)
            .where(RegionCommerceStoreOrm.adstrd_code == _TEST_ADSTRD)
        ).scalar_one()
    assert count == 1
    _cleanup()
