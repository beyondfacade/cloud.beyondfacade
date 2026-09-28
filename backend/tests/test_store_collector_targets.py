"""수집기 타깃 빌더 — 슬러그당 타깃 1개, 업종 집합·접두는 분류기가 정한다 (테스트 DB 시드 기준)."""

from apps.store.adapter.inbound.cli.store_collector import _build_targets


def test_general_restaurants_is_one_target_per_district_with_food_industry_set():
    targets = _build_targets("강남구", "general_restaurants")
    assert len(targets) == 1
    t = targets[0]
    assert t.slug == "general_restaurants"
    assert t.authority_code == "3220000"
    assert t.industry_id == "restaurant_other"  # 앵커
    assert t.store_prefix == "restaurant"
    assert set(t.industry_ids) == {
        "korean_food", "chinese_food", "japanese_food", "western_food", "snack", "chicken", "pub", "restaurant_other",
    }


def test_existing_slug_targets_are_unchanged():
    targets = _build_targets(None, "karaoke")
    assert len(targets) == 25
    assert {t.slug for t in targets} == {"karaoke_rooms"}
    assert all(t.industry_ids == ("karaoke",) and t.store_prefix is None for t in targets)


def test_filter_accepts_industry_id_or_slug():
    assert _build_targets("강남구", "restaurant_other")[0].slug == "general_restaurants"
    assert _build_targets("강남구", "karaoke_rooms")[0].industry_id == "karaoke"


def test_all_targets_have_one_per_slug_per_district():
    targets = _build_targets("강남구", None)
    slugs = [t.slug for t in targets]
    assert len(slugs) == len(set(slugs))  # 같은 슬러그가 두 번 나오면 데이터셋을 중복 수집한다
    assert "general_restaurants" in slugs and "karaoke_rooms" in slugs
