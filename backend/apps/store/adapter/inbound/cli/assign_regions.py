"""점포 행정동 공간조인 러너 (Driving Adapter, CLI).

- 입력: region.geometry_ref의 경계 GeoJSON(v0.6.0 적재) × store.lat/lng
- 판정: shapely STRtree 포함(contains) 일괄 질의 → 미포함은 최근접 경계 허용 오차 내 스냅
  (DB에 PostGIS 없음 — pgvector 이미지 — 이라 앱사이드 조인이 현 인프라 정합)
- 멱등: 기본은 region_code IS NULL 행만 채움. --full 은 전체 재판정 (경계 갱신 시)
- 일일 증분(store-collector 크론) 후속 실행을 전제로 설계

실행: python -m apps.store.adapter.inbound.cli.assign_regions [--full]
"""

import argparse
import json
from pathlib import Path

import shapely
from shapely import STRtree
from sqlalchemy import select, update

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
# 경계 틈·좌표 변환 오차 흡수 스냅 한계 — 서울 위도에서 0.0005° ≈ 44~56m
# (EPSG:5174→WGS84 변환 오차 ±3m 실측 + 인접 폴리곤 사이 미세 틈 대비)
_NEAREST_TOLERANCE_DEG = 0.0005
_UPDATE_CHUNK = 10_000


class RegionIndex:
    """(region_code, GeoJSON geometry) 목록의 공간 인덱스 — 점→행정동 판정."""

    def __init__(self, items: list[tuple[str, dict]]) -> None:
        self._codes = [code for code, _ in items]
        self._geoms = shapely.from_geojson(
            json.dumps(
                {
                    "type": "GeometryCollection",
                    "geometries": [geometry for _, geometry in items],
                }
            )
        ).geoms
        self._tree = STRtree(list(self._geoms))

    @classmethod
    def from_refs(cls, repo_root: Path, refs: list[tuple[str, str]]) -> "RegionIndex":
        """refs: [(region_code, geometry_ref 상대경로)] — 파일에서 geometry만 읽는다."""
        items = []
        for region_code, ref in refs:
            feature = json.loads((repo_root / ref).read_text(encoding="utf-8"))
            items.append((region_code, feature["geometry"]))
        return cls(items)

    def locate_many(self, lngs: list[float], lats: list[float]) -> list[str | None]:
        points = shapely.points(lngs, lats)
        result: list[str | None] = [None] * len(points)
        for point_idx, geom_idx in zip(*self._tree.query(points, predicate="within")):
            result[point_idx] = self._codes[geom_idx]
        for i, code in enumerate(result):
            if code is None:
                nearest = self._tree.nearest(points[i])
                if points[i].distance(self._geoms[int(nearest)]) <= _NEAREST_TOLERANCE_DEG:
                    result[i] = self._codes[int(nearest)]
        return result

    def locate(self, lng: float, lat: float) -> str | None:
        return self.locate_many([lng], [lat])[0]


def assign_all(full: bool = False) -> None:
    with session_scope() as session:
        refs = session.execute(
            select(RegionOrm.region_code, RegionOrm.geometry_ref).where(
                RegionOrm.geometry_ref.is_not(None)
            )
        ).all()
        index = RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])
        print(f"경계 인덱스: {len(refs)}개 행정동")

        stmt = select(
            StoreOrm.store_id, StoreOrm.lng, StoreOrm.lat, StoreOrm.district_code
        ).where(StoreOrm.lat.is_not(None), StoreOrm.lng.is_not(None))
        if not full:
            stmt = stmt.where(StoreOrm.region_code.is_(None))
        rows = session.execute(stmt).all()
        print(f"판정 대상: {len(rows)}건")
        if not rows:
            return

        codes = index.locate_many([r.lng for r in rows], [r.lat for r in rows])

        updates = [
            {"store_id": row.store_id, "region_code": code}
            for row, code in zip(rows, codes)
            if code is not None
        ]
        for start in range(0, len(updates), _UPDATE_CHUNK):
            session.execute(update(StoreOrm), updates[start : start + _UPDATE_CHUNK])

        unassigned = len(rows) - len(updates)
        # 교차검증: 판정된 행정동의 소속 구 vs 인허가 관할 구 (경계 인접부는 정상 불일치 가능)
        district_by_region = {
            rc: dc
            for rc, dc in session.execute(select(RegionOrm.region_code, RegionOrm.district_code))
        }
        mismatch = sum(
            1
            for row, code in zip(rows, codes)
            if code is not None and district_by_region.get(code) != row.district_code
        )
        print(f"기입: {len(updates)}건 / 미판정: {unassigned}건 / 구 교차 불일치: {mismatch}건")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="region_code 기존 값 포함 전체 재판정")
    args = parser.parse_args()
    assign_all(full=args.full)


if __name__ == "__main__":
    main()
