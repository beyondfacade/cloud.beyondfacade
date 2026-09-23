"""파서가 쓰는 마스터 사전 — 도메인은 DB를 모른다. 어댑터가 채워서 함수 인자로 넘긴다."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

# 번호·'제'·구분점을 지운 기본 이름 — 사람은 "역삼동"이라 말하고 마스터는 "역삼1동"이다
_NUMBERING = re.compile(r"[제\d.·]+")


def base_name(region_name: str) -> str:
    return _NUMBERING.sub("", region_name)


@dataclass(frozen=True)
class RegionEntry:
    region_code: str
    name: str
    district_code: str
    district_name: str


@dataclass(frozen=True)
class MasterDictionary:
    regions: Sequence[RegionEntry]
    districts: dict[str, str]  # 구 이름 → district_code
    industry_names: dict[str, str]  # industry_id → 한국어 이름
    # 이름(정확·기본) → 그 이름으로 불릴 수 있는 동들. 정확 이름과 기본 이름이 같으면 한 번만
    _by_name: dict[str, tuple[RegionEntry, ...]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        index: dict[str, list[RegionEntry]] = {}
        for entry in self.regions:
            for key in {entry.name, base_name(entry.name)}:
                index.setdefault(key, []).append(entry)
        object.__setattr__(self, "_by_name", {k: tuple(v) for k, v in index.items()})

    def region_names_longest_first(self) -> list[str]:
        return sorted(self._by_name, key=len, reverse=True)

    def regions_named(self, name: str) -> tuple[RegionEntry, ...]:
        return self._by_name.get(name, ())

    def district_names_longest_first(self) -> list[str]:
        return sorted(self.districts, key=len, reverse=True)

    def region_by_code(self, region_code: str) -> RegionEntry | None:
        return next((r for r in self.regions if r.region_code == region_code), None)
