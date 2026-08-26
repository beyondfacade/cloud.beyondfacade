"""점포 공간조인 — RegionIndex 포함 판정·경계 틈 보정 검증."""

from apps.store.adapter.inbound.cli.assign_regions import RegionIndex

# 단위 정사각형 2개 (인접, 공유 변 x=1)
_LEFT = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
}
_RIGHT = {
    "type": "MultiPolygon",
    "coordinates": [[[[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0], [1.0, 0.0]]]],
}


def _index() -> RegionIndex:
    return RegionIndex([("LEFT", _LEFT), ("RIGHT", _RIGHT)])


def test_locate_point_inside_polygon():
    assert _index().locate(0.5, 0.5) == "LEFT"
    assert _index().locate(1.5, 0.5) == "RIGHT"


def test_locate_gap_point_snaps_to_nearest_within_tolerance():
    # 폴리곤 밖이지만 경계에서 허용 오차(≈50m) 이내 — 좌표 변환 오차(±3m)·경계 틈 흡수
    assert _index().locate(-0.0001, 0.5) == "LEFT"
    assert _index().locate(2.0001, 0.5) == "RIGHT"


def test_locate_far_outside_returns_none():
    assert _index().locate(5.0, 5.0) is None
    assert _index().locate(0.5, 3.0) is None


def test_locate_many_matches_singular():
    index = _index()
    assert index.locate_many([0.5, 1.5, 5.0], [0.5, 0.5, 5.0]) == ["LEFT", "RIGHT", None]
