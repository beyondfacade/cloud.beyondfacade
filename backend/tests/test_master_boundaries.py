"""행정동 경계 적재 — 동명 정규화·adm_cd↔region_code 매칭 검증.

실데이터 근거 (2026-08-26 브이월드 실호출):
- WFS lt_c_cademd(행정동)는 통계청 코드(adm_cd 8자리)라 region_code(행안부 10자리)와 직접 조인 불가
- 표기 차이: DB "창신제1동" vs WFS "창신1동", DB "면목제3.8동" vs WFS "면목3·8동"
- 함정: "홍제1동"은 동명 자체에 '제'가 포함 — WFS 쪽 이름에서 '제'를 지우면 안 됨
"""

import json

from apps.master.adapter.inbound.cli.load_boundaries import (
    build_mapping,
    normalize_db_name,
    normalize_wfs_name,
    write_boundary_file,
)


def test_normalize_db_name_strips_je_before_digit():
    assert normalize_db_name("창신제1동") == "창신1동"
    assert normalize_db_name("면목제3.8동") == "면목38동"
    # 동명 자체의 '홍제'는 보존, 서수 '제'만 제거
    assert normalize_db_name("홍제제1동") == "홍제1동"


def test_normalize_wfs_name_keeps_je_in_proper_name():
    # WFS 원천엔 서수 '제'가 없으므로 제거 규칙을 적용하지 않는다 (홍제1동 → 홍1동 방지)
    assert normalize_wfs_name("홍제1동") == "홍제1동"
    assert normalize_wfs_name("면목3·8동") == "면목38동"
    assert normalize_wfs_name("종로1·2·3·4가동") == "종로1234가동"


def test_build_mapping_matches_unique_names():
    wfs = [{"adm_cd": "11010720", "adm_nm": "청운효자동"}]
    db = [("1111051500", "청운효자동", "종로구")]
    mapping, unmatched = build_mapping(wfs, db)
    assert mapping == {"11010720": "1111051500"}
    assert unmatched == []


def test_build_mapping_resolves_duplicate_dong_names_by_learned_gu():
    # 신사동은 강남구·관악구에 모두 존재 — 같은 구의 유일 동에서 학습한 구코드로 해소
    wfs = [
        {"adm_cd": "11230510", "adm_nm": "압구정동"},  # 강남구 유일 동 → 11230=강남구 학습
        {"adm_cd": "11230600", "adm_nm": "신사동"},
        {"adm_cd": "11210520", "adm_nm": "은천동"},  # 관악구 유일 동 → 11210=관악구 학습
        {"adm_cd": "11210600", "adm_nm": "신사동"},
    ]
    db = [
        ("1168051000", "압구정동", "강남구"),
        ("1168052000", "신사동", "강남구"),
        ("1162051000", "은천동", "관악구"),
        ("1162052000", "신사동", "관악구"),
    ]
    mapping, unmatched = build_mapping(wfs, db)
    assert mapping["11230600"] == "1168052000"
    assert mapping["11210600"] == "1162052000"
    assert unmatched == []


def test_build_mapping_reports_unmatched_wfs_dong():
    # 용신동: 경계 기준일(2024-06-30) 이후 분동돼 DB엔 용두동·신설동만 존재
    wfs = [{"adm_cd": "11060810", "adm_nm": "용신동"}]
    db = [("1123051500", "신설동", "동대문구"), ("1123053300", "용두동", "동대문구")]
    mapping, unmatched = build_mapping(wfs, db)
    assert mapping == {}
    assert unmatched == [("11060810", "용신동")]


def test_build_mapping_rejects_duplicate_region_assignment():
    # 서로 다른 WFS 동이 같은 region으로 몰리면 매칭 로직 오류 — 조용히 넘어가면 안 됨
    wfs = [
        {"adm_cd": "11010720", "adm_nm": "청운효자동"},
        {"adm_cd": "11010730", "adm_nm": "청운 효자동"},  # 공백 차이만 있는 중복
    ]
    db = [("1111051500", "청운효자동", "종로구")]
    try:
        build_mapping(wfs, db)
    except ValueError as exc:
        assert "1111051500" in str(exc)
    else:
        raise AssertionError("중복 배정인데 ValueError가 나지 않음")


def test_write_boundary_file_roundtrip(tmp_path):
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": [[[[127.0, 37.5], [127.1, 37.5], [127.1, 37.6], [127.0, 37.5]]]]},
        "properties": {"adm_cd": "11010720", "adm_nm": "청운효자동", "base_date": "20240630"},
    }
    path = write_boundary_file(
        tmp_path, "1111051500", feature, source_layer="lt_c_cademd"
    )
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "1111051500.json"
    assert saved["geometry"]["type"] == "MultiPolygon"
    props = saved["properties"]
    assert props["region_code"] == "1111051500"
    assert props["source_layer"] == "lt_c_cademd"
    assert props["adm_cd"] == "11010720"
    assert props["base_date"] == "20240630"
