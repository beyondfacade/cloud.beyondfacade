"""편의점 개폐업 이력 — 담배소매인 인허가를 편의점 개폐업의 대리 원천으로 읽는다 (업종 특화 신호 설계서 §5).
순수 파이썬. 브랜드 사전(옛 이름 포함)으로 편의점 행만 고르고, 같은 자리 양도·양수는 한 에피소드로 접는다."""

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date

MIN_VALID_DATE = date(1990, 1, 1)  # 원천에 1900-01-01 쓰레기값이 있다
# 같은 지번에서 폐업 ±90일 안 새 지정 = 승계. 실측(9/29) 편의점 폐업 15,573건 중 2,482건(16%)
SUCCESSION_GAP_DAYS = 90

# 브랜드 사전 (CLAUDE.md §5 — if/elif 대신 순서 있는 매핑, 첫 일치가 이긴다). 대문자화한 상호에 re.search.
# 옛 이름: LG25·엘지25 → GS25, 훼미리마트·패밀리마트 → CU, 바이더웨이·코리아세븐 → 세븐일레븐, 위드미 → 이마트24.
# 'CU'는 영문자 경계 필수(CUBE·SCU). 맨 '세븐'·맨 '로그인'·'GS리테일'(GS수퍼 혼재)은 넣지 않는다.
BRAND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (brand, re.compile("|".join(patterns)))
    for brand, patterns in (
        ("GS25", (r"GS\s*25", r"지에스\s*25", r"LG\s*25", r"엘지\s*25")),
        ("CU", (r"(?<![A-Z])CU(?![A-Z])", r"씨유", r"훼미리\s*마트", r"패밀리\s*마트", r"FAMILY\s*MART", r"비지에프")),
        ("세븐일레븐", (r"세븐\s*-?\s*일레븐", r"7\s*-?\s*ELEVEN", r"(?<!\d)7-11(?!\d)", r"바이더웨이",
                   r"BUY\s*THE\s*WAY", r"코리아세븐")),
        ("이마트24", (r"이마트\s*24", r"EMART\s*24", r"위드미", r"WITH\s*ME")),
        ("미니스톱", (r"미니스톱", r"MINI\s*STOP")),
        ("기타 체인", (r"365\s*플러스", r"홈플러스\s*365", r"스토리웨이", r"씨스페이스", r"C-?\s*SPACE", r"로그인\s*25")),
    )
)


def brand_of(name: str) -> str | None:
    """편의점 브랜드 — 사전에 없으면 None(편의점이 아니거나 개인 편의점: 판정 원천에서 뺀다)."""
    text = name.upper()
    return next((brand for brand, pattern in BRAND_PATTERNS if pattern.search(text)), None)


@dataclass(frozen=True)
class RetailerRecord:
    retailer_id: str
    name: str
    region_code: str | None
    open_date: date | None  # 지정일자 또는 인허가일자 (둘 다 있으면 실측 전부 같다)
    close_date: date | None  # 폐업일자 또는 인허가취소일자
    address_key: str | None  # 지번주소 공백 정규화 — 승계 판단 단위


@dataclass(frozen=True)
class Episode:
    """한 자리의 편의점 영업 한 토막 — 승계로 이어진 레코드 여러 개가 하나가 된다."""

    region_code: str
    open_date: date
    close_date: date | None
    record_count: int = 1


def address_key(jibun_address: str | None) -> str | None:
    if jibun_address is None or not jibun_address.strip():
        return None
    return " ".join(jibun_address.split())


def fold_successions(records: Iterable[RetailerRecord], gap_days: int = SUCCESSION_GAP_DAYS) -> list[Episode]:
    """레코드 → 에피소드. 같은 지번에서 이미 닫힌 에피소드의 폐업일 ±gap_days 안에 개업하면 그 에피소드에 잇는다.
    영업 중인 에피소드에는 잇지 않는다(대형 건물 동시 영업). 주소 없는 레코드는 혼자 에피소드."""
    usable = [r for r in records if r.region_code and r.open_date and r.open_date >= MIN_VALID_DATE]
    by_address: dict[str, list[RetailerRecord]] = {}
    episodes: list[Episode] = []
    for record in usable:
        if record.address_key is None:
            episodes.append(_start(record))
        else:
            by_address.setdefault(record.address_key, []).append(record)
    for group in by_address.values():
        episodes.extend(_fold_group(sorted(group, key=lambda r: (r.open_date, r.retailer_id)), gap_days))
    return episodes


def _start(record: RetailerRecord) -> Episode:
    return Episode(record.region_code, record.open_date, record.close_date)


def _fold_group(records: list[RetailerRecord], gap_days: int) -> list[Episode]:
    episodes: list[Episode] = []
    for record in records:
        nearest = min(
            (
                (abs((record.open_date - e.close_date).days), n)
                for n, e in enumerate(episodes)
                if e.close_date is not None and abs((record.open_date - e.close_date).days) <= gap_days
            ),
            default=None,
        )
        if nearest is None:
            episodes.append(_start(record))
            continue
        e = episodes[nearest[1]]
        close = None if record.close_date is None else max(e.close_date, record.close_date)
        episodes[nearest[1]] = replace(e, close_date=close, record_count=e.record_count + 1)
    return episodes
