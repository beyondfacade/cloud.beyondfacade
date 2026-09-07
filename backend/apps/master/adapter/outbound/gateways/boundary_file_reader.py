"""Driven Adapter — geometry_ref(repo root 상대경로)의 경계 GeoJSON Feature 파일 판독."""

import json
from pathlib import Path

from apps.master.app.ports.output.region_port import RegionBoundaryReaderPort

_REPO_ROOT = Path(__file__).resolve().parents[6]


class BoundaryFileReader(RegionBoundaryReaderPort):
    def read_feature(self, geometry_ref: str) -> dict:
        return json.loads((_REPO_ROOT / geometry_ref).read_text(encoding="utf-8"))
