"""담배소매인 지정 현황 적재 러너 (Driving Adapter, CLI).

- 원천: 지방행정 인허가 「기타_담배소매업」 서울 아카이브 CSV
  (data/raw/tobacco_retail/*.csv, CP949 — 2026-08-25 확보 불변 원본, API 호출 0회)
- 좌표: EPSG:5174 평면직각 → WGS84 변환 + 서울 근방 범위 검증 (store BC 전례)
- 자치구: 개방자치단체코드 ↔ district.opn_authority_code (25개 구 전수 실측)
- 멱등: PK(관리번호) INSERT … ON CONFLICT DO UPDATE — region_code는 건드리지 않아
  공간조인 기입값을 보존. 적재 후 region 공간조인(store RegionIndex 재사용)까지 수행
- 원천이 정적 아카이브라 크론 비대상 — 갱신은 파일 재확보 후 재실행 (멱등)

실행: python -m apps.tobacco.adapter.inbound.cli.load_tobacco_retailer [--skip-assign]
"""

import argparse
import calendar
import csv
import glob
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from pyproj import Transformer
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm

# 공간 인덱스는 store BC의 검증된 유틸을 읽기 전용 재사용 (타 BC 무수정 — adapter 레이어 간 import)
from apps.store.adapter.inbound.cli.assign_regions import RegionIndex
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from apps.tobacco.domain.entities.tobacco_retailer_entity import TobaccoRetailer
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_CSV_GLOB = str(_REPO_ROOT / "data" / "raw" / "tobacco_retail" / "*.csv")
_TRANSFORMER = Transformer.from_crs(5174, 4326, always_xy=True)

# 변환 결과 검증 범위 (서울 근방) — 벗어나면 좌표 오류로 보고 버림 (store 전례와 동일)
_LAT_RANGE = (37.0, 38.2)
_LNG_RANGE = (126.3, 127.6)
_UPSERT_BATCH = 4000  # 14컬럼 × 4000 = 56,000 파라미터 < psycopg 한도 65,535
_UPDATE_CHUNK = 10_000


def _clamp_ymd(text: str) -> tuple[int, int, int] | None:
    """원천에 실존하는 불량 날짜(예: 2006-02-29) 방어 — 일(day)을 월말로 클램프."""
    try:
        year, month, day = (int(p) for p in text.split("-"))
        if not (1 <= month <= 12) or year < 1 or day < 1:
            return None
        return year, month, min(day, calendar.monthrange(year, month)[1])
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    ymd = _clamp_ymd(value.strip()[:10])
    return date(*ymd) if ymd else None


def _to_wgs84(x_raw: str, y_raw: str) -> tuple[float | None, float | None]:
    if not x_raw.strip() or not y_raw.strip():
        return None, None
    lng, lat = _TRANSFORMER.transform(float(x_raw), float(y_raw))
    if _LAT_RANGE[0] < lat < _LAT_RANGE[1] and _LNG_RANGE[0] < lng < _LNG_RANGE[1]:
        return round(lat, 7), round(lng, 7)
    return None, None


def parse_retailer(
    row: dict[str, str], district_by_authority: dict[str, str]
) -> TobaccoRetailer | None:
    """CSV 1행 → 엔티티. 미지의 자치단체코드는 None (스킵·건수 보고)."""
    district_code = district_by_authority.get(row["개방자치단체코드"].strip())
    if district_code is None:
        return None
    lat, lng = _to_wgs84(row["좌표정보(X)"], row["좌표정보(Y)"])
    return TobaccoRetailer(
        retailer_id=row["관리번호"].strip(),
        name=row["사업장명"].strip(),
        district_code=district_code,
        status_code=row["상세영업상태코드"].strip(),
        status_name=row["상세영업상태명"].strip(),
        designated_date=_parse_date(row["지정일자"]),
        permit_date=_parse_date(row["인허가일자"]),
        close_date=_parse_date(row["폐업일자"]),
        cancel_date=_parse_date(row["인허가취소일자"]),
        lat=lat,
        lng=lng,
        road_address=row["도로명주소"].strip() or None,
        jibun_address=row["지번주소"].strip() or None,
        source_updated_at=datetime.fromisoformat(row["데이터갱신시점"].strip()),
    )


def _row_values(retailer: TobaccoRetailer) -> dict:
    return {
        "retailer_id": retailer.retailer_id,
        "name": retailer.name,
        "district_code": retailer.district_code,
        "status_code": retailer.status_code,
        "status_name": retailer.status_name,
        "designated_date": retailer.designated_date,
        "permit_date": retailer.permit_date,
        "close_date": retailer.close_date,
        "cancel_date": retailer.cancel_date,
        "lat": retailer.lat,
        "lng": retailer.lng,
        "road_address": retailer.road_address,
        "jibun_address": retailer.jibun_address,
        "source_updated_at": retailer.source_updated_at,
    }


def upsert_retailers(retailers: list[TobaccoRetailer]) -> int:
    """PK(관리번호) 충돌 시 원천 컬럼만 갱신 — region_code(공간조인 결과)는 보존. 멱등."""
    count = 0
    with session_scope() as session:
        for start in range(0, len(retailers), _UPSERT_BATCH):
            batch = retailers[start : start + _UPSERT_BATCH]
            statement = insert(TobaccoRetailerOrm).values([_row_values(r) for r in batch])
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=["retailer_id"],
                    set_={
                        column: getattr(statement.excluded, column)
                        for column in _row_values(batch[0])
                        if column != "retailer_id"
                    },
                )
            )
            count += len(batch)
    return count


def assign_regions() -> None:
    """좌표 보유·region 미기입 행만 행정동 공간조인 — store assign_regions와 동일 판정."""
    with session_scope() as session:
        refs = session.execute(
            select(RegionOrm.region_code, RegionOrm.geometry_ref).where(
                RegionOrm.geometry_ref.is_not(None)
            )
        ).all()
        index = RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])
        rows = session.execute(
            select(TobaccoRetailerOrm.retailer_id, TobaccoRetailerOrm.lng, TobaccoRetailerOrm.lat)
            .where(
                TobaccoRetailerOrm.lat.is_not(None),
                TobaccoRetailerOrm.lng.is_not(None),
                TobaccoRetailerOrm.region_code.is_(None),
            )
        ).all()
        print(f"공간조인 대상: {len(rows)}건 (경계 {len(refs)}개 행정동)")
        if not rows:
            return
        codes = index.locate_many([r.lng for r in rows], [r.lat for r in rows])
        updates = [
            {"retailer_id": row.retailer_id, "region_code": code}
            for row, code in zip(rows, codes)
            if code is not None
        ]
        for start in range(0, len(updates), _UPDATE_CHUNK):
            session.execute(update(TobaccoRetailerOrm), updates[start : start + _UPDATE_CHUNK])
        print(f"region 기입: {len(updates)}건 / 미판정: {len(rows) - len(updates)}건")


def load_all(skip_assign: bool = False) -> None:
    paths = sorted(glob.glob(_CSV_GLOB))
    if not paths:
        raise FileNotFoundError(f"담배소매업 CSV 없음: {_CSV_GLOB}")
    with session_scope() as session:
        district_by_authority = {
            authority: code
            for code, authority in session.execute(
                select(DistrictOrm.district_code, DistrictOrm.opn_authority_code).where(
                    DistrictOrm.opn_authority_code.is_not(None)
                )
            )
        }
    retailers: list[TobaccoRetailer] = []
    skipped = 0
    for path in paths:
        with open(path, encoding="cp949", newline="") as f:
            for row in csv.DictReader(f):
                retailer = parse_retailer(row, district_by_authority)
                if retailer is None:
                    skipped += 1
                else:
                    retailers.append(retailer)
    count = upsert_retailers(retailers)
    by_status = Counter(r.status_name for r in retailers)
    with_coord = sum(1 for r in retailers if r.lat is not None)
    print(
        f"tobacco retailer loader: {count}행 업서트 (자치구 미매칭 스킵 {skipped})"
        f" — 좌표 {with_coord}건({with_coord / count:.1%}), 상태 {dict(by_status)}"
    )
    if not skip_assign:
        assign_regions()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-assign", action="store_true", help="행정동 공간조인 생략")
    args = parser.parse_args()
    load_all(skip_assign=args.skip_assign)


if __name__ == "__main__":
    main()
