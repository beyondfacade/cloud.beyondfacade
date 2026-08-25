"""마스터 계층 시드 러너 (Driving Adapter, CLI).

- district/region: 주민등록 인구세대 CSV의 행정기관코드에서 파싱 (실데이터 기반 — ERD 원칙)
- industry/subcategory/source_code: brainstorming §3.5·§3.6, docs/api.md 확정 코드
- 멱등: PK 기준 merge — 재실행해도 중복 없음

실행: python -m apps.master.adapter.inbound.cli.seed_master
"""

import glob
import re
import unicodedata
from pathlib import Path

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.master.adapter.outbound.orms.industry_subcategory_orm import IndustrySubcategoryOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_JUMIN_DIR = Path(__file__).resolve().parents[6] / "data" / "raw" / "jumin"
_CODE_PATTERN = re.compile(r"\((\d{10})\)\s*$")

# 업종 10종 — (industry_id, 이름, 수요동인)
_INDUSTRIES = [
    ("cafe", "카페", "daily"),
    ("convenience_store", "편의점", "daily"),
    ("hair_salon", "미용실", "daily"),
    ("karaoke", "노래방", "leisure"),
    ("pc_bang", "PC방", "leisure"),
    ("gym", "헬스장", "leisure"),
    ("billiard", "당구장", "leisure"),
    ("real_estate", "부동산중개업", "macro"),
    ("academy", "학원", "demographic"),
    ("childcare", "어린이집", "demographic"),
]

# 확정된 원천 코드만 시드 (미확정: 편의점 상가정보 업종코드 — 확정 시 추가)
_SOURCE_CODES = [
    ("cafe", "mois_permit", "rest_cafes"),
    ("hair_salon", "mois_permit", "beauty_salons"),
    ("karaoke", "mois_permit", "karaoke_rooms"),
    ("pc_bang", "mois_permit", "pc_bangs"),
    ("gym", "mois_permit", "fitness_centers"),
    ("billiard", "mois_permit", "billiard_halls"),
    ("real_estate", "molit_broker", "15123990"),
    ("academy", "seoul_academy", "OA-20528"),
    ("childcare", "childcare_portal", "15013108"),
]

# 인허가 API 개방자치단체코드 (2026-08-25 karaoke_rooms/info 실응답에서 구명 교차확인)
_OPN_AUTHORITY_CODES = {
    "종로구": "3000000", "중구": "3010000", "용산구": "3020000", "성동구": "3030000",
    "광진구": "3040000", "동대문구": "3050000", "중랑구": "3060000", "성북구": "3070000",
    "강북구": "3080000", "도봉구": "3090000", "노원구": "3100000", "은평구": "3110000",
    "서대문구": "3120000", "마포구": "3130000", "양천구": "3140000", "강서구": "3150000",
    "구로구": "3160000", "금천구": "3170000", "영등포구": "3180000", "동작구": "3190000",
    "관악구": "3200000", "서초구": "3210000", "강남구": "3220000", "송파구": "3230000",
    "강동구": "3240000",
}

# 학원 교습계열 5 + 미용업 세분 3 (brainstorming §3.5·§3.6)
_SUBCATEGORIES = [
    ("academy_exam", "academy", "교습계열", "입시·보습"),
    ("academy_arts", "academy", "교습계열", "예체능"),
    ("academy_language", "academy", "교습계열", "외국어"),
    ("academy_vocational", "academy", "교습계열", "직업·기술"),
    ("academy_studyroom", "academy", "교습계열", "독서실·스터디"),
    ("hair_general", "hair_salon", "미용세분", "일반(헤어)"),
    ("hair_skin", "hair_salon", "미용세분", "피부"),
    ("hair_nail", "hair_salon", "미용세분", "네일"),
]


def _parse_seoul_admin_codes(jumin_dir: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """인구세대 CSV 1개에서 (자치구, 행정동) 목록을 파싱한다."""
    candidates = [
        p for p in glob.glob(str(jumin_dir / "*.csv"))
        if unicodedata.normalize("NFC", Path(p).name).startswith("인구세대")
    ]
    if not candidates:
        raise FileNotFoundError(f"인구세대 CSV 없음: {jumin_dir}")

    districts: list[tuple[str, str]] = []
    regions: list[tuple[str, str, str]] = []
    with open(sorted(candidates)[-1], encoding="cp949") as f:
        for line in f:
            head = line.split(",")[0].strip().strip('"')
            if not head.startswith("서울"):
                continue
            code_match = _CODE_PATTERN.search(head)
            if not code_match:
                continue
            code = code_match.group(1)
            names = head[: code_match.start()].split()
            if len(names) == 2:  # 자치구: "서울특별시 종로구 (1111000000)"
                districts.append((code[:5], names[1]))
            elif len(names) == 3:  # 행정동: "서울특별시 종로구 청운효자동(1111051500)"
                regions.append((code, code[:5], names[2]))
    return districts, regions


def seed_all(jumin_dir: Path = _JUMIN_DIR) -> None:
    districts, regions = _parse_seoul_admin_codes(jumin_dir)

    with session_scope() as session:
        for district_code, name in districts:
            session.merge(
                DistrictOrm(
                    district_code=district_code,
                    name=name,
                    opn_authority_code=_OPN_AUTHORITY_CODES.get(name),
                )
            )
        for region_code, district_code, name in regions:
            session.merge(RegionOrm(region_code=region_code, district_code=district_code, name=name))
        for industry_id, name, demand_type in _INDUSTRIES:
            session.merge(IndustryOrm(industry_id=industry_id, name=name, demand_type=demand_type))
        for subcategory_id, industry_id, axis, target in _SUBCATEGORIES:
            session.merge(
                IndustrySubcategoryOrm(
                    subcategory_id=subcategory_id,
                    industry_id=industry_id,
                    category_axis=axis,
                    target_group=target,
                )
            )

        existing = {
            (row.industry_id, row.source_system, row.code)
            for row in session.query(IndustrySourceCodeOrm)
        }
        for industry_id, source_system, code in _SOURCE_CODES:
            if (industry_id, source_system, code) not in existing:
                session.add(
                    IndustrySourceCodeOrm(
                        industry_id=industry_id, source_system=source_system, code=code
                    )
                )


if __name__ == "__main__":
    seed_all()
    print("master seed 완료")
