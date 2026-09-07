"""주민등록 연령별 인구 적재 러너 (Driving Adapter, CLI).

- 원천: 행안부 주민등록 연령별 인구현황 CSV 아카이브 (data/raw/jumin/연령별*.csv,
  분기 파일·CP949·wide format — 열 = {YYYY년MM월}_{계|남|여}_{연령구간})
- 변환: wide → long (region_code, period, gender, age_from) — 계·총인구수는 도출값이라 미저장
- 범위: 2019~2025 각년 12월 + 2026 최신월 (docs/api.md ⑩, 연 단위 축)
- 매칭: 행정구역명 끝 행정기관코드 10자리 ↔ region.region_code (seed_master 파싱 전례)
  region에 없는 행정동(폐지동 등)은 스킵하고 건수 보고
- 멱등: PK(region_code, period, gender, age_from) 기준 INSERT … ON CONFLICT DO UPDATE

실행: python -m apps.master.adapter.inbound.cli.load_population
"""

import csv
import glob
import re
import unicodedata
from collections.abc import Iterable, Iterator
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_JUMIN_DIR = Path(__file__).resolve().parents[6] / "data" / "raw" / "jumin"
_CODE_PATTERN = re.compile(r"\((\d{10})\)\s*$")  # seed_master와 동일 — 행정기관코드
_FILE_PATTERN = re.compile(r"^연령별(\d{6})_(\d{6})")  # 파일명이 담는 연월 구간
_COLUMN_PATTERN = re.compile(r"^(\d{4})년(\d{2})월_(남|여)_(.+)$")
_AGE_RANGE_PATTERN = re.compile(r"^(\d+)~(\d+)세$")
_AGE_OPEN_PATTERN = re.compile(r"^(\d+)세 이상$")
_GENDER_CODES = {"남": "M", "여": "F"}

# 적재 대상 연월 — 2019~2025 각년 12월 + 2026 최신월(아카이브 최신분)
TARGET_PERIODS = [
    "201912", "202012", "202112", "202212", "202312", "202412", "202512", "202606",
]

_UPSERT_BATCH = 5000

# (region_code, gender, age_from, age_to, population)
Record = tuple[str, str, int, int | None, int]


def find_age_file(period: str, jumin_dir: Path = _JUMIN_DIR) -> Path:
    """대상 연월을 포함하는 분기 CSV를 찾는다 (파일명 구간 [시작, 끝] 판정)."""
    for path in sorted(glob.glob(str(jumin_dir / "*.csv"))):
        match = _FILE_PATTERN.match(unicodedata.normalize("NFC", Path(path).name))
        if match and match.group(1) <= period <= match.group(2):
            return Path(path)
    raise FileNotFoundError(f"연령별 CSV 없음: {jumin_dir} period={period}")


def parse_age_columns(header: list[str], period: str) -> dict[int, tuple[str, int, int | None]]:
    """헤더에서 대상 연월의 남/여 연령구간 컬럼만 골라 {인덱스: (성별, age_from, age_to)}."""
    columns: dict[int, tuple[str, int, int | None]] = {}
    for index, name in enumerate(header):
        match = _COLUMN_PATTERN.match(unicodedata.normalize("NFC", name.strip()))
        if not match or match.group(1) + match.group(2) != period:
            continue
        gender, age_label = _GENDER_CODES[match.group(3)], match.group(4).strip()
        if ranged := _AGE_RANGE_PATTERN.match(age_label):
            columns[index] = (gender, int(ranged.group(1)), int(ranged.group(2)))
        elif open_ended := _AGE_OPEN_PATTERN.match(age_label):
            columns[index] = (gender, int(open_ended.group(1)), None)
    return columns


def parse_population_records(
    rows: Iterator[list[str]], period: str, region_codes: set[str]
) -> tuple[list[Record], set[str]]:
    """CSV 행(첫 행 = 헤더) → (적재 레코드, region 미매칭 행정동 코드).

    행정동 판별: 서울 접두 + 코드 앞 이름 3어절(시·구·동) — 시 총계·자치구 행은 제외.
    """
    columns = parse_age_columns(next(rows), period)
    records: list[Record] = []
    skipped: set[str] = set()
    for row in rows:
        head = row[0].strip()
        if not head.startswith("서울"):
            continue
        code_match = _CODE_PATTERN.search(head)
        if not code_match or len(head[: code_match.start()].split()) != 3:
            continue  # 시 총계·자치구
        code = code_match.group(1)
        if code not in region_codes:
            skipped.add(code)
            continue
        for index, (gender, age_from, age_to) in columns.items():
            value = row[index].strip().replace(",", "")
            records.append((code, gender, age_from, age_to, int(value) if value else 0))
    return records, skipped


def _upsert(session: Session, period: str, records: Iterable[Record]) -> None:
    """PK 충돌 시 인구수만 갱신 — 재실행 멱등."""
    values = [
        {
            "region_code": code,
            "period": period,
            "gender": gender,
            "age_from": age_from,
            "age_to": age_to,
            "population": population,
        }
        for code, gender, age_from, age_to, population in records
    ]
    for start in range(0, len(values), _UPSERT_BATCH):
        statement = insert(PopulationStatOrm).values(values[start : start + _UPSERT_BATCH])
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["region_code", "period", "gender", "age_from"],
                set_={
                    "age_to": statement.excluded.age_to,
                    "population": statement.excluded.population,
                },
            )
        )


def load_all(jumin_dir: Path = _JUMIN_DIR, periods: list[str] = TARGET_PERIODS) -> None:
    with session_scope() as session:
        region_codes = set(session.execute(select(RegionOrm.region_code)).scalars())
        for period in periods:
            path = find_age_file(period, jumin_dir)
            with open(path, encoding="cp949", newline="") as f:
                records, skipped = parse_population_records(csv.reader(f), period, region_codes)
            _upsert(session, period, records)
            regions = len({r[0] for r in records})
            print(
                f"{period}: {len(records)}행 업서트 (행정동 {regions}/{len(region_codes)},"
                f" 미매칭 스킵 {len(skipped)}동)"
            )


if __name__ == "__main__":
    load_all()
    print("population_stat 적재 완료")
