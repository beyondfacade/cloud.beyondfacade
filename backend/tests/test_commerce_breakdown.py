"""commerce 분해(1NF long) 적재 검증 — 헤더 순서 매핑 + 23행 전개 + 축 합계 + 멱등 업서트.

고정하는 실측 사실 (설계서 §4-1, 원천 343,167행 전수 확인):
- 원천 헤더 오타 `시간대_건수~06_매출_건수` — 이름이 아니라 순서로 잡아야 한다
- weekpart·dow·hour 세 축은 총액의 완전 분할이다 (개별 행 최대 오차 금액 5원·건수 5건)
- gender·age 두 축은 완전 분할이 **아니다** — 인구속성 미상 거래가 빠져 금액 89.2%·건수 95.9%만 덮는다
"""

from pathlib import Path

from sqlalchemy import delete, func, select

from apps.commerce.adapter.outbound.gateways.seoul_commerce_csv_gateway import (
    BREAKDOWN_DIMENSIONS,
    SeoulCommerceSalesBreakdownCsvGateway,
    breakdown_columns,
)
from apps.commerce.adapter.outbound.orms.region_commerce_sales_breakdown_orm import (
    RegionCommerceSalesBreakdownOrm,
)
from apps.commerce.adapter.outbound.orms.region_commerce_sales_orm import RegionCommerceSalesOrm
from apps.commerce.adapter.outbound.repositories.region_commerce_sales_breakdown_repository import (
    SqlAlchemyRegionCommerceSalesBreakdownRepository,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_sales_repository import (
    SqlAlchemyRegionCommerceSalesRepository,
)
from apps.commerce.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.commerce.app.use_cases.region_commerce_sales_breakdown_interactor import (
    RegionCommerceSalesBreakdownIngestInteractor,
)
from apps.commerce.domain.entities.region_commerce_sales_breakdown_entity import (
    RegionCommerceSalesBreakdown,
)
from apps.commerce.domain.entities.region_commerce_sales_entity import RegionCommerceSales
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_ADSTRD = "99999999"
_TEST_INDUSTRY = "TS900001"

# 실CSV 53컬럼 헤더 실측 사본 (2026-09-23 확보분 5파일 전부 동일).
# 시간대 건수 6종의 오타를 그대로 옮겼다 — 이름으로 찾으면 안 된다는 사실을 테스트가 고정한다.
_FULL_HEADER = ",".join(
    [
        "기준_년분기_코드",
        "행정동_코드",
        "행정동_코드_명",
        "서비스_업종_코드",
        "서비스_업종_코드_명",
        "당월_매출_금액",
        "당월_매출_건수",
        "주중_매출_금액",
        "주말_매출_금액",
        "월요일_매출_금액",
        "화요일_매출_금액",
        "수요일_매출_금액",
        "목요일_매출_금액",
        "금요일_매출_금액",
        "토요일_매출_금액",
        "일요일_매출_금액",
        "시간대_00~06_매출_금액",
        "시간대_06~11_매출_금액",
        "시간대_11~14_매출_금액",
        "시간대_14~17_매출_금액",
        "시간대_17~21_매출_금액",
        "시간대_21~24_매출_금액",
        "남성_매출_금액",
        "여성_매출_금액",
        "연령대_10_매출_금액",
        "연령대_20_매출_금액",
        "연령대_30_매출_금액",
        "연령대_40_매출_금액",
        "연령대_50_매출_금액",
        "연령대_60_이상_매출_금액",
        "주중_매출_건수",
        "주말_매출_건수",
        "월요일_매출_건수",
        "화요일_매출_건수",
        "수요일_매출_건수",
        "목요일_매출_건수",
        "금요일_매출_건수",
        "토요일_매출_건수",
        "일요일_매출_건수",
        "시간대_건수~06_매출_건수",  # 오타 — `시간대_00~06_매출_건수`가 아니다
        "시간대_건수~11_매출_건수",
        "시간대_건수~14_매출_건수",
        "시간대_건수~17_매출_건수",
        "시간대_건수~21_매출_건수",
        "시간대_건수~24_매출_건수",
        "남성_매출_건수",
        "여성_매출_건수",
        "연령대_10_매출_건수",
        "연령대_20_매출_건수",
        "연령대_30_매출_건수",
        "연령대_40_매출_건수",
        "연령대_50_매출_건수",
        "연령대_60_이상_매출_건수",
    ]
)

# 금액은 1000 + 구간번호(0~22), 건수는 100 + 구간번호 — 어느 구간이 어디에 붙는지 값으로 식별된다
_AMOUNTS = [1000 + offset for offset in range(23)]
_COUNTS = [100 + offset for offset in range(23)]
_FULL_ROW = ",".join(
    ["20251", "11110515", "청운효자동", "CS100010", "커피-음료", "999999", "8888"]
    + [str(value) for value in _AMOUNTS]
    + [str(value) for value in _COUNTS]
)


def _cp949_csv(tmp_path: Path, name: str, header: str, *rows: str) -> Path:
    path = tmp_path / name
    path.write_text("\n".join([header, *rows]) + "\n", encoding="cp949")
    return path


# ---------- 헤더 순서 기반 컬럼 매핑 ----------


def test_breakdown_columns_map_typo_hour_count_columns_by_position():
    """시간대 건수 6종은 헤더 이름이 `시간대_건수~NN`이라 이름으로는 구간을 알 수 없다."""
    columns = breakdown_columns(_FULL_HEADER.split(","))
    assert len(columns) == 23

    hours = [column for column in columns if column.dim_type == "hour"]
    assert [column.dim_key for column in hours] == [
        "00_06",
        "06_11",
        "11_14",
        "14_17",
        "17_21",
        "21_24",
    ]
    # 금액 쪽은 정상 표기, 건수 쪽은 오타 표기 — 같은 구간에 짝지어져야 한다
    assert [column.amount_column for column in hours] == [
        "시간대_00~06_매출_금액",
        "시간대_06~11_매출_금액",
        "시간대_11~14_매출_금액",
        "시간대_14~17_매출_금액",
        "시간대_17~21_매출_금액",
        "시간대_21~24_매출_금액",
    ]
    assert [column.count_column for column in hours] == [
        "시간대_건수~06_매출_건수",
        "시간대_건수~11_매출_건수",
        "시간대_건수~14_매출_건수",
        "시간대_건수~17_매출_건수",
        "시간대_건수~21_매출_건수",
        "시간대_건수~24_매출_건수",
    ]
    # 첫 구간(주중)은 총계 2컬럼 바로 뒤, 건수 블록은 23칸 뒤에서 시작한다
    assert (columns[0].amount_index, columns[0].count_index) == (7, 30)


def test_breakdown_columns_reject_changed_source_layout():
    """레이아웃이 바뀌면 조용히 엉뚱한 구간에 붙는 대신 즉시 깨져야 한다."""
    header = _FULL_HEADER.split(",")[:-1]
    try:
        breakdown_columns(header)
    except ValueError as error:
        assert "레이아웃" in str(error)
    else:
        raise AssertionError("헤더 컬럼 수가 모자라면 ValueError여야 한다")


# ---------- 원본 1행 → 23행 전개 ----------


def test_one_source_row_expands_to_23_dimension_rows(tmp_path):
    path = _cp949_csv(tmp_path, "sales.csv", _FULL_HEADER, _FULL_ROW)
    rows = list(SeoulCommerceSalesBreakdownCsvGateway().fetch_breakdown(path))

    assert len(rows) == 23
    assert {(row.dim_type, row.dim_key) for row in rows} == set(BREAKDOWN_DIMENSIONS)
    axis_sizes = {axis: 0 for axis in ("weekpart", "dow", "hour", "gender", "age")}
    for row in rows:
        axis_sizes[row.dim_type] += 1
    assert axis_sizes == {"weekpart": 2, "dow": 7, "hour": 6, "gender": 2, "age": 6}

    by_key = {(row.dim_type, row.dim_key): row for row in rows}
    assert (by_key[("weekpart", "weekday")].amount, by_key[("weekpart", "weekday")].count) == (
        1000,
        100,
    )
    # 시간대 00_06은 금액 블록 10번째(offset 9), 건수 블록 10번째 — 오타 컬럼이 제 짝을 찾는다
    assert (by_key[("hour", "00_06")].amount, by_key[("hour", "00_06")].count) == (1009, 109)
    assert (by_key[("hour", "21_24")].amount, by_key[("hour", "21_24")].count) == (1014, 114)
    assert (by_key[("age", "60_over")].amount, by_key[("age", "60_over")].count) == (1022, 122)

    identity = {(row.adstrd_code, row.service_industry_code, row.year_quarter) for row in rows}
    assert identity == {("11110515", "CS100010", "20251")}  # 년분기는 정수가 아니라 문자열
    assert all(row.region_code is None for row in rows)  # 해석은 인터랙터 몫


def test_blank_breakdown_measures_stay_null_not_zero(tmp_path):
    """'매출 0원'과 '측정 없음'은 다르다 (childcare EW_CNT_TOT 전례)."""
    blank_row = ",".join(
        ["20251", "11110515", "청운효자동", "CS100010", "커피-음료", "999999", "8888"]
        + [""] * 46
    )
    path = _cp949_csv(tmp_path, "sales.csv", _FULL_HEADER, blank_row)
    rows = list(SeoulCommerceSalesBreakdownCsvGateway().fetch_breakdown(path))
    assert len(rows) == 23
    assert all(row.amount is None and row.count is None for row in rows)


# ---------- 축 합계 (원천 품질 고정) ----------


def test_weekpart_dow_hour_axes_partition_the_total(tmp_path):
    """세 축은 총액의 완전 분할이다 — 실 원천 1행(청운효자동 한식음식점 2024Q1)으로 고정한다."""
    real_row = (
        "20241,11110515,청운효자동,CS100001,한식음식점,3282036149,102492,"
        # 금액 23: 주중/주말 · 월~일 · 시간대 6 · 남/여 · 연령 6
        "2359720647,922315502,"
        "437604243,492152225,464403243,496560053,468999883,466527570,455788932,"
        "119530946,346096639,806654241,527741745,896394194,585618384,"
        "1302939731,1215407774,"
        "42259619,533861294,730302339,589949096,393324308,228650838,"
        # 건수 23
        "74296,28196,"
        "13816,15268,14556,15505,15151,14311,13885,"
        "3036,12233,26947,17041,26224,17011,"
        "44988,45432,"
        "1746,16744,22903,21103,16401,11530"
    )
    path = _cp949_csv(tmp_path, "sales.csv", _FULL_HEADER, real_row)
    rows = list(SeoulCommerceSalesBreakdownCsvGateway().fetch_breakdown(path))
    total_amount, total_count = 3282036149, 102492

    for axis in ("weekpart", "dow", "hour"):
        amount = sum(row.amount for row in rows if row.dim_type == axis)
        count = sum(row.count for row in rows if row.dim_type == axis)
        assert amount == total_amount, axis
        assert count == total_count, axis

    # gender·age는 완전 분할이 아니다 — 인구속성 미상 거래가 빠진다 (원천 전수 실측: 금액 89.2%)
    for axis in ("gender", "age"):
        amount = sum(row.amount for row in rows if row.dim_type == axis)
        assert amount < total_amount, axis
        assert amount / total_amount < 0.8, axis


# ---------- region 해석 ----------


class _FakeRegionCatalog(RegionCatalogPort):
    def region_code_by_adstrd(self) -> dict[str, str]:
        return {"11110515": "1111051500"}


class _FakeBreakdownGateway:
    def __init__(self, rows):
        self._rows = rows

    def fetch_breakdown(self, path):
        return iter(self._rows)


class _RecordingRepository:
    def __init__(self):
        self.rows = []

    def upsert(self, rows):
        self.rows.extend(rows)
        return len(rows)


def _breakdown(adstrd_code: str, dim_key: str = "weekday") -> RegionCommerceSalesBreakdown:
    return RegionCommerceSalesBreakdown(
        adstrd_code=adstrd_code,
        service_industry_code="CS100010",
        year_quarter="20251",
        dim_type="weekpart",
        dim_key=dim_key,
        region_code=None,
        amount=100,
        count=2,
    )


def test_ingest_resolves_8digit_prefix_and_keeps_unmatched_rows():
    """원천에만 있는 옛 행정동(용신동 11230536)은 버리지 않고 region_code NULL로 적재한다."""
    repository = _RecordingRepository()
    interactor = RegionCommerceSalesBreakdownIngestInteractor(
        repository=repository,
        gateway=_FakeBreakdownGateway([_breakdown("11110515"), _breakdown("11230536")]),
        region_catalog=_FakeRegionCatalog(),
    )
    result = interactor.ingest([Path("unused.csv")])
    assert result.processed == 2
    assert (result.region_resolved, result.region_unresolved) == (1, 1)
    assert [row.region_code for row in repository.rows] == ["1111051500", None]


def test_ingest_streams_in_chunks_without_materializing_the_file(monkeypatch):
    """789만 행을 한 리스트로 들지 않는다 — 청크 크기마다 업서트가 끊겨야 한다."""
    monkeypatch.setattr(
        "apps.commerce.app.use_cases.region_commerce_sales_breakdown_interactor.CHUNK_SIZE",
        3,
    )

    class _CountingRepository(_RecordingRepository):
        def __init__(self):
            super().__init__()
            self.calls = []

        def upsert(self, rows):
            self.calls.append(len(rows))
            return super().upsert(rows)

    repository = _CountingRepository()
    rows = [_breakdown("11110515", dim_key=f"k{index}") for index in range(7)]
    interactor = RegionCommerceSalesBreakdownIngestInteractor(
        repository=repository,
        gateway=_FakeBreakdownGateway(rows),
        region_catalog=_FakeRegionCatalog(),
    )
    assert interactor.ingest([Path("unused.csv")]).processed == 7
    assert repository.calls == [3, 3, 1]


# ---------- 멱등 업서트 (실 DB) ----------


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(RegionCommerceSalesBreakdownOrm).where(
                RegionCommerceSalesBreakdownOrm.adstrd_code == _TEST_ADSTRD
            )
        )
        session.execute(
            delete(RegionCommerceSalesOrm).where(
                RegionCommerceSalesOrm.adstrd_code == _TEST_ADSTRD
            )
        )


def _breakdown_entity(amount: int) -> RegionCommerceSalesBreakdown:
    return RegionCommerceSalesBreakdown(
        adstrd_code=_TEST_ADSTRD,
        service_industry_code=_TEST_INDUSTRY,
        year_quarter="20251",
        dim_type="hour",
        dim_key="00_06",
        region_code=None,
        amount=amount,
        count=2,
    )


def test_breakdown_upsert_is_idempotent_and_updates_values():
    """같은 PK 재적재로 행이 늘지 않고 값만 갱신된다. 부모 sales 행이 복합 FK를 통과시킨다."""
    _cleanup()
    SqlAlchemyRegionCommerceSalesRepository().upsert(
        [
            RegionCommerceSales(
                adstrd_code=_TEST_ADSTRD,
                service_industry_code=_TEST_INDUSTRY,
                year_quarter="20251",
                region_code=None,
                sales_amount=100,
                sales_count=2,
            )
        ]
    )
    repository = SqlAlchemyRegionCommerceSalesBreakdownRepository()
    assert repository.upsert([_breakdown_entity(10)]) == 1
    assert repository.upsert([_breakdown_entity(20)]) == 1
    with session_scope() as session:
        rows = (
            session.execute(
                select(RegionCommerceSalesBreakdownOrm).where(
                    RegionCommerceSalesBreakdownOrm.adstrd_code == _TEST_ADSTRD
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].amount == 20
    assert (rows[0].dim_type, rows[0].dim_key) == ("hour", "00_06")
    _cleanup()


def test_breakdown_requires_parent_sales_row():
    """총액 없는 분해 행은 DB가 막는다 — 복합 FK를 두는 이유."""
    _cleanup()
    try:
        SqlAlchemyRegionCommerceSalesBreakdownRepository().upsert([_breakdown_entity(10)])
    except Exception as error:  # psycopg ForeignKeyViolation
        assert "fk_region_commerce_sales_breakdown_parent" in str(error)
    else:
        raise AssertionError("부모 행 없이 분해 행이 들어가면 안 된다")
    finally:
        _cleanup()


def test_full_wiring_ingests_real_layout_csv_idempotently(tmp_path):
    """게이트웨이→인터랙터→리포지토리 전 배선을 같은 파일로 두 번 태워도 행 수가 변하지 않는다."""
    _cleanup()
    SqlAlchemyRegionCommerceSalesRepository().upsert(
        [
            RegionCommerceSales(
                adstrd_code=_TEST_ADSTRD,
                service_industry_code=_TEST_INDUSTRY,
                year_quarter="20251",
                region_code=None,
                sales_amount=999999,
                sales_count=8888,
            )
        ]
    )
    row = _FULL_ROW.replace("11110515", _TEST_ADSTRD).replace("CS100010", _TEST_INDUSTRY)
    path = _cp949_csv(tmp_path, "sales.csv", _FULL_HEADER, row)
    interactor = RegionCommerceSalesBreakdownIngestInteractor(
        repository=SqlAlchemyRegionCommerceSalesBreakdownRepository(),
        gateway=SeoulCommerceSalesBreakdownCsvGateway(),
        region_catalog=_FakeRegionCatalog(),
    )
    assert interactor.ingest([path]).processed == 23
    assert interactor.ingest([path]).processed == 23
    with session_scope() as session:
        count = session.execute(
            select(func.count())
            .select_from(RegionCommerceSalesBreakdownOrm)
            .where(RegionCommerceSalesBreakdownOrm.adstrd_code == _TEST_ADSTRD)
        ).scalar_one()
    assert count == 23  # 원본 1행 → 23행, 재실행해도 그대로
    _cleanup()
