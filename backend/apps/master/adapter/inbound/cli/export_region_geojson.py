"""행정동 경계 정적 파일 내보내기 (Driving Adapter, CLI).

- 산출: frontend/public/geojson/seoul-regions.geojson — 프론트 지도·관문이 API 대신 받는 정적 파일 (serverplan K3)
- 내용: GET /regions/geojson과 같은 FeatureCollection(좌표 5자리, properties = DB region_code·name)
- 언제: load_boundaries로 경계를 다시 적재했거나 region.name이 바뀌었을 때. 실행 후 프론트에 커밋한다.

실행: python -m apps.master.adapter.inbound.cli.export_region_geojson
"""

import json
from pathlib import Path

from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.dependencies.region_dependencies import get_region_use_case

_REPO_ROOT = Path(__file__).resolve().parents[6]
_OUT_PATH = _REPO_ROOT / "frontend" / "public" / "geojson" / "seoul-regions.geojson"


def export(use_case: RegionUseCase, out_path: Path) -> int:
    collection = use_case.geojson()
    out_path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(collection["features"])


if __name__ == "__main__":
    count = export(get_region_use_case(), _OUT_PATH)
    print(f"행정동 경계 {count}개 → {_OUT_PATH.relative_to(_REPO_ROOT)}")
