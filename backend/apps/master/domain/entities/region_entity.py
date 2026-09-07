from dataclasses import dataclass


@dataclass
class Region:
    """행정동 (서울 ~427개) — 행정기관코드 10자리."""

    region_code: str
    district_code: str
    name: str
    geometry_ref: str | None = None  # 경계 GeoJSON 경로 (repo root 상대)
