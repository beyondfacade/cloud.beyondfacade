"""추출기 체인이 채워 가는 초안 — 각 추출기는 자기 몫만 채우고 다음으로 넘긴다."""

from dataclasses import dataclass, field, replace

from apps.intent.domain.value_objects.master_dictionary import RegionEntry


@dataclass(frozen=True)
class IntentDraft:
    region_code: str | None = None
    region_name: str | None = None
    district_code: str | None = None
    industry_id: str | None = None
    budget_krw: int | None = None
    # 동명이동·번호 동처럼 하나로 못 정한 경우 — 되묻기 칩의 재료
    candidates: tuple[RegionEntry, ...] = field(default_factory=tuple)
    llm_used: bool = False

    def with_region(self, entry: RegionEntry) -> "IntentDraft":
        return replace(
            self,
            region_code=entry.region_code,
            region_name=entry.name,
            district_code=entry.district_code,
            candidates=(),
        )

    @property
    def intent_type(self) -> str:
        if self.region_code and self.industry_id:
            return "A"
        if self.region_code:
            return "B"
        return "C"

    @property
    def missing(self) -> list[str]:
        return [
            key
            for key, value in (
                ("region", self.region_code),
                ("industry", self.industry_id),
                ("budget", self.budget_krw),
            )
            if value is None
        ]
