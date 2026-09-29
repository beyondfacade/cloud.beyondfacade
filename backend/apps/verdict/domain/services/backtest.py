"""백테스트 집계 — T 시점 판정과 그 뒤 진입 코호트의 실제 폐업을 (동, 업종)으로 조인해 판정 코드별로 센다 (설계서 §13).
순수 파이썬. 폐업률·lift는 버킷이 스스로 계산한다."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict

VERDICT_ORDER: tuple[str, ...] = ("red", "orange", "clear", "insufficient")


def quarter_before(as_of: date) -> str:
    """as_of가 속한 분기의 직전 분기 라벨('20221') — T 시점에 확정돼 있던 마지막 분기."""
    quarter = (as_of.month - 1) // 3 + 1
    return f"{as_of.year - 1}4" if quarter == 1 else f"{as_of.year}{quarter - 1}"


@dataclass(frozen=True)
class OutcomeBucket:
    industry_id: str | None  # None = 전체
    verdict_code: str
    pairs: int  # 동×업종 조합 수 (개업 0인 조합 포함)
    opened: int
    closed: int

    @property
    def rate(self) -> float | None:
        return None if self.opened == 0 else self.closed / self.opened


def summarize(verdicts: Sequence[RegionIndustryVerdict], outcomes: Iterable[EntrantOutcome]) -> list[OutcomeBucket]:
    """전체 버킷(industry_id None) 다음에 업종별 버킷. 판정이 없는 결과 행은 버린다."""
    by_key = {(o.region_code, o.industry_id): o for o in outcomes}
    acc: dict[tuple[str | None, str], list[int]] = {}
    for v in verdicts:
        o = by_key.get((v.region_code, v.industry_id))
        opened, closed = (o.opened, o.closed_within) if o else (0, 0)
        for industry in (None, v.industry_id):
            cell = acc.setdefault((industry, v.verdict_code), [0, 0, 0])
            cell[0] += 1
            cell[1] += opened
            cell[2] += closed
    ordered = sorted(acc, key=lambda k: (k[0] is not None, k[0] or "", VERDICT_ORDER.index(k[1])))
    return [OutcomeBucket(industry, code, *acc[(industry, code)]) for industry, code in ordered]
