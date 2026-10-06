"""행정동 경계 적재 — 원천 vuski/admdongkor(통계청 SGIS 행정동 경계 가공, CC BY 4.0) 매칭 검증.

브이월드 경계는 약관상 사전 승낙 없는 저장·재배포가 안 돼 원천을 바꿨다(BE v0.84.0).
admdongkor는 행안부 10자리 코드(adm_cd2)를 실어 region_code와 바로 맞는다 — 동명 매칭·법정동 보충이 필요 없다.
"""

import json

from apps.master.adapter.inbound.cli.load_boundaries import match_features, write_boundary_file


def _feature(code: str) -> dict:
    return {"type": "Feature", "geometry": None, "properties": {"adm_cd2": code, "adm_nm": f"서울특별시 {code}"}}


def test_경계는_행안부_코드로_region과_바로_맞추고_서울_밖과_모르는_코드는_뺀다():
    features = [_feature("1111051500"), _feature("1168064000"), _feature("2611051000"), _feature("1199999999")]

    matched, missing = match_features(features, ["1111051500", "1168064000", "1123053300"])

    assert {code: f["properties"]["adm_cd2"] for code, f in matched.items()} == {
        "1111051500": "1111051500", "1168064000": "1168064000",
    }
    assert missing == ["1123053300"]


def test_write_boundary_file_roundtrip(tmp_path):
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": [[[[127.0, 37.5], [127.1, 37.5], [127.1, 37.6], [127.0, 37.5]]]]},
        "properties": {"adm_cd": "11010720", "adm_nm": "청운효자동", "base_date": "20240630"},
    }
    path = write_boundary_file(
        tmp_path, "1111051500", feature, source_layer="admdongkor ver20260701"
    )
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "1111051500.json"
    assert saved["geometry"]["type"] == "MultiPolygon"
    props = saved["properties"]
    assert props["region_code"] == "1111051500"
    assert props["source_layer"] == "admdongkor ver20260701"
    assert props["adm_cd"] == "11010720"
    assert props["base_date"] == "20240630"
