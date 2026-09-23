"""공고 지역 판정 — 서울 창업자에게 해당하는 것만 남긴다 (설계서 §3).

`hashtags`는 쉼표 구분 태그 목록이고 앞쪽에 분야·시도 태그가 온다. 2026-09-23 실측(미만료 2,032건):

- `서울` 태그가 있고 전 시도를 덮지는 않음 → **서울 전용**
- 전 시도를 덮거나 `전국` 태그 → **전국**. 전국 공고는 "시도 언급 없음"이 아니라 시도를 전부 단다
- 그 외 → 타 시도, 제외

**원천이 시도 어휘를 두 벌 섞어 쓴다.** `전남광주`(통합 명칭) 512건과 `광주`·`전남`(282·281건)이
공존해, 전국 공고의 지역 태그 수가 16개(통합 어휘)거나 17개(분리 어휘)다. 태그 수를 세면 16개짜리
353건이 전국으로 안 잡혀 "서울 전용"이 된다 — `전남광주`를 `전남`+`광주`로 **펴서** 17개 기준
커버리지로 판정한다. `전국` 태그는 3건뿐이라 이것만 믿을 수 없다.

태그만으로는 부족하다. **과천시 이자차액보전처럼 17개 시도를 전부 달아둔 지자체 공고가 26건** 있어
소관기관이 서울 밖 지자체면 태그와 무관하게 제외한다. 서울 자치구 25개는 `district` 마스터로 받는다
(하드코딩하면 마스터와 어긋날 자리가 생긴다).

오탐이 나오면 아래 사전과 접미사 목록만 고친다.
"""

from collections.abc import Iterable

SIDO_NAMES: tuple[str, ...] = (
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
)

NATIONWIDE_TAG = "전국"

# 원천이 쓰는 통합·별칭 표기 → 표준 시도. 새 표기가 나오면 여기만 늘린다
_TAG_ALIASES: dict[str, tuple[str, ...]] = {
    "전남광주": ("전남", "광주"),
}

REGION_SEOUL = "seoul"
REGION_NATIONWIDE = "nationwide"

REGION_LABELS: dict[str, str] = {REGION_SEOUL: "서울", REGION_NATIONWIDE: "전국"}

# 지자체 이름의 끝 — "중소벤처기업부"(부)·"한국무역보험공사"(사)는 걸리지 않는다
_LOCAL_GOV_SUFFIXES: tuple[str, ...] = ("특별자치시", "특별자치도", "광역시", "시", "군", "구", "도")


def _tags(hashtags: str | None) -> set[str]:
    return {tag.strip() for tag in (hashtags or "").split(",") if tag.strip()}


def covered_sido(hashtags: str | None) -> set[str]:
    """태그에서 표준 시도 집합을 뽑는다 — 통합 표기(`전남광주`)는 펴서 센다."""
    tags = _tags(hashtags)
    covered = {sido for sido in SIDO_NAMES if sido in tags}
    for alias, expanded in _TAG_ALIASES.items():
        if alias in tags:
            covered.update(expanded)
    return covered


def is_outside_seoul_local_gov(org: str | None, seoul_district_names: Iterable[str]) -> bool:
    """소관기관이 서울 밖 지자체인가 — 태그를 이겨 제외시킨다."""
    name = (org or "").strip()
    if not name:
        return False
    if "서울" in name or name in set(seoul_district_names):
        return False
    return name.endswith(_LOCAL_GOV_SUFFIXES)


def classify_region(
    hashtags: str | None, org: str | None, seoul_district_names: Iterable[str]
) -> str | None:
    """`seoul` · `nationwide` · None(해당 없음)."""
    if is_outside_seoul_local_gov(org, seoul_district_names):
        return None
    tags = _tags(hashtags)
    covered = covered_sido(hashtags)
    if NATIONWIDE_TAG in tags or len(covered) == len(SIDO_NAMES):
        return REGION_NATIONWIDE
    if "서울" in covered:
        return REGION_SEOUL
    return None
