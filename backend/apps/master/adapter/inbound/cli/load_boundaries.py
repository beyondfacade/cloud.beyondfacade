"""행정동 경계 적재 러너 (Driving Adapter, CLI).

- 원천: vuski/admdongkor 버전 고정 파일(통계청 SGIS 행정동 경계 가공, CC BY 4.0 — 출처표시 필수, 화면 /sources)
- 매칭: adm_cd2(행안부 10자리) = region_code
- 산출: data/geojson/regions/{region_code}.json 저장 후 region.geometry_ref 갱신 (멱등)
- 경계를 바꾼 뒤에는 점포 동 재배정(`assign_regions --full`) → 지표(`build_metrics`) → 판정(`build_verdicts`)을 다시 돈다

실행: python -m apps.master.adapter.inbound.cli.load_boundaries
"""

import json
from pathlib import Path

from sqlalchemy import select

from apps.master.adapter.outbound.gateways.admdongkor_boundary_gateway import VERSION, AdmdongkorBoundaryGateway
# region.district_code FK 대상이 메타데이터에 있어야 flush된다
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_GEOJSON_DIR = _REPO_ROOT / "data" / "geojson" / "regions"


def match_features(features: list[dict], region_codes: list[str]) -> tuple[dict[str, dict], list[str]]:
    """adm_cd2(행안부 10자리) = region_code로 바로 맞춘다. 반환: ({region_code: feature}, 경계 없는 region_code)."""
    by_code = {str(f["properties"]["adm_cd2"]): f for f in features}
    matched = {code: by_code[code] for code in region_codes if code in by_code}
    return matched, [code for code in region_codes if code not in by_code]


def write_boundary_file(
    directory: Path, region_code: str, feature: dict, source_layer: str
) -> Path:
    """경계 Feature를 region_code 명의로 저장 — 원천 추적용 provenance를 properties에 남긴다."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{region_code}.json"
    saved = {
        "type": "Feature",
        "geometry": feature["geometry"],
        "properties": {**feature["properties"], "region_code": region_code, "source_layer": source_layer},
    }
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    return path


def load_all(geojson_dir: Path = _GEOJSON_DIR) -> None:
    features = AdmdongkorBoundaryGateway().fetch_seoul_admin_dongs()
    print(f"admdongkor {VERSION} 서울 행정동 수신: {len(features)}건")

    with session_scope() as session:
        regions = list(session.execute(select(RegionOrm)).scalars())
        matched, missing = match_features(features, [r.region_code for r in regions])
        for region in regions:
            if region.region_code in matched:
                path = write_boundary_file(
                    geojson_dir, region.region_code, matched[region.region_code], source_layer=f"admdongkor {VERSION}"
                )
                region.geometry_ref = str(path.relative_to(_REPO_ROOT))
        print(f"geometry_ref 기입: {len(matched)}/{len(regions)}")
        if missing:
            print(f"경계 없는 region: {missing}")


if __name__ == "__main__":
    load_all()
