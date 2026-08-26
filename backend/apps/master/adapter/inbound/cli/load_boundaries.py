"""행정동 경계 적재 러너 (Driving Adapter, CLI).

- 원천: 브이월드 WFS lt_c_cademd (행정동, 기준일 2024-06-30, 통계청 adm_cd 8자리)
- 매칭: adm_cd↔region_code(행안부 10자리)는 코드 체계가 달라 직접 조인 불가
  → (구, 정규화 동명)으로 매칭. 구는 유일 동명에서 학습한 adm_cd 앞 5자리로 해소
- 보충: 경계 기준일 이후 분동된 용두동·신설동(행정동 용신동의 후신)은
  법정동 경계(LT_C_ADEMD_INFO)로 1:1 대체 — 분동 후 행정동 경계 = 법정동 경계
- 산출: data/geojson/regions/{region_code}.json 저장 후 region.geometry_ref 갱신 (멱등)

실행: python -m apps.master.adapter.inbound.cli.load_boundaries
"""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from apps.master.adapter.outbound.gateways.vworld_boundary_gateway import (
    VworldBoundaryGateway,
)
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_GEOJSON_DIR = _REPO_ROOT / "data" / "geojson" / "regions"

# 분동(2024-07 이후)으로 행정동 WFS에 경계가 없는 region — 법정동 경계로 보충
# (2026-08-26 실호출: 동대문구 법정동 신설동=11230101, 용두동=11230102)
_LEGAL_DONG_SUPPLEMENTS = {
    "1123051500": "11230101",  # 신설동
    "1123053300": "11230102",  # 용두동
}


def normalize_wfs_name(name: str) -> str:
    """WFS 동명 정규화 — 구분 기호만 제거 ('홍제1동'의 '제'는 동명이므로 보존)."""
    return re.sub(r"[·.,\s]", "", unicodedata.normalize("NFC", name))


def normalize_db_name(name: str) -> str:
    """DB 동명 정규화 — 구분 기호 제거 후 서수 '제'(숫자 앞)만 추가 제거 (창신제1동→창신1동)."""
    return re.sub(r"제(?=\d)", "", normalize_wfs_name(name))


def build_mapping(
    wfs_props: list[dict], db_rows: list[tuple[str, str, str]]
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """adm_cd → region_code 매핑을 만든다.

    wfs_props: [{"adm_cd", "adm_nm"}], db_rows: [(region_code, 동명, 구명)]
    반환: (매핑, 미매칭 WFS 동 목록). 같은 region 중복 배정은 ValueError.
    """
    dong_candidates: dict[str, list[tuple[str, str]]] = defaultdict(list)  # 동명 → [(구명, region_code)]
    for region_code, name, district_name in db_rows:
        dong_candidates[normalize_db_name(name)].append((district_name, region_code))

    mapping: dict[str, str] = {}
    ambiguous: list[tuple[str, str, list[tuple[str, str]]]] = []
    unmatched: list[tuple[str, str]] = []
    gu_names: dict[str, str] = {}  # adm_cd 앞 5자리(통계청 구코드) → 구명 (유일 동에서 학습)

    for props in wfs_props:
        adm_cd, adm_nm = props["adm_cd"], props["adm_nm"]
        candidates = dong_candidates.get(normalize_wfs_name(adm_nm), [])
        if len(candidates) == 1:
            mapping[adm_cd] = candidates[0][1]
            gu_names.setdefault(adm_cd[:5], candidates[0][0])
        elif candidates:
            ambiguous.append((adm_cd, adm_nm, candidates))
        else:
            unmatched.append((adm_cd, adm_nm))

    for adm_cd, adm_nm, candidates in ambiguous:
        hits = [rc for gu, rc in candidates if gu == gu_names.get(adm_cd[:5])]
        if len(hits) != 1:
            raise ValueError(f"구 학습으로 해소 불가: {adm_cd} {adm_nm} 후보 {candidates}")
        mapping[adm_cd] = hits[0]

    duplicates = defaultdict(list)
    for adm_cd, region_code in mapping.items():
        duplicates[region_code].append(adm_cd)
    collided = {rc: cds for rc, cds in duplicates.items() if len(cds) > 1}
    if collided:
        raise ValueError(f"region 중복 배정: {collided}")
    return mapping, unmatched


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
    gateway = VworldBoundaryGateway()
    features = gateway.fetch_seoul_admin_dongs()
    print(f"WFS 행정동 수신: {len(features)}건")

    with session_scope() as session:
        rows = session.execute(
            select(RegionOrm.region_code, RegionOrm.name, DistrictOrm.name).join(
                DistrictOrm, RegionOrm.district_code == DistrictOrm.district_code
            )
        ).all()
        mapping, unmatched = build_mapping(
            [f["properties"] for f in features], [tuple(r) for r in rows]
        )
        print(f"매칭: {len(mapping)}/{len(rows)}, 미매칭 WFS: {unmatched}")

        feature_by_adm_cd = {f["properties"]["adm_cd"]: f for f in features}
        refs: dict[str, str] = {}
        for adm_cd, region_code in mapping.items():
            path = write_boundary_file(
                geojson_dir, region_code, feature_by_adm_cd[adm_cd], source_layer="lt_c_cademd"
            )
            refs[region_code] = str(path.relative_to(_REPO_ROOT))

        for region_code, emd_cd in _LEGAL_DONG_SUPPLEMENTS.items():
            feature = gateway.fetch_legal_dong(emd_cd)
            path = write_boundary_file(
                geojson_dir, region_code, feature, source_layer="LT_C_ADEMD_INFO"
            )
            refs[region_code] = str(path.relative_to(_REPO_ROOT))
        print(f"법정동 보충: {len(_LEGAL_DONG_SUPPLEMENTS)}건")

        for region in session.execute(select(RegionOrm)).scalars():
            if region.region_code in refs:
                region.geometry_ref = refs[region.region_code]

        total = len(rows)
        filled = len(refs)
        print(f"geometry_ref 기입: {filled}/{total}")
        if filled != total:
            missing = {r[0] for r in rows} - set(refs)
            print(f"경계 없는 region: {sorted(missing)}")


if __name__ == "__main__":
    load_all()
