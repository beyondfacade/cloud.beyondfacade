"""Driven Adapter — 부동산 생존자 역산 DB 읽기 전용 (store·commerce ORM). cross-BC 접근은 이 파일 안에서만 (컨트롤러 P6).
연도별: 현재 영업 사무소 등록 연도별 수(store) vs 아카이브 같은 연도 개업 수 합(region_commerce_store CS200033).
동별(2021~2023): 같은 두 값을 region_code로 묶는다. 분석 전용(읽기만) — `real_estate_survivor_backcast` CLI가 호출한다."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import extract, func, select

from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm as S
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

_INDUSTRY = "real_estate"
_ARCHIVE_CODE = "CS200033"


@dataclass(frozen=True)
class SurvivorBackcastData:
    survivors_by_year: dict[int, int]
    archive_opens_by_year: dict[int, int]
    dong_survivors: dict[str, int]
    dong_archive_opens: dict[str, int]


class SurvivorBackcastGateway:
    def fetch(self, years: Sequence[int], dong_years: Sequence[int]) -> SurvivorBackcastData:
        open_year = extract("year", StoreOrm.open_date)
        live = (StoreOrm.industry_id == _INDUSTRY, StoreOrm.close_date.is_(None), StoreOrm.region_code.is_not(None))
        archive_year = func.substr(S.year_quarter, 1, 4)
        with session_scope() as session:
            survivors = {
                int(y): n
                for y, n in session.execute(
                    select(open_year, func.count()).where(*live, open_year.in_(years)).group_by(open_year)
                ).all()
            }
            archive = {
                int(y): int(n)
                for y, n in session.execute(
                    select(archive_year, func.sum(S.open_store_count))
                    .where(S.service_industry_code == _ARCHIVE_CODE)
                    .group_by(archive_year)
                ).all()
            }
            dong_survivors = dict(
                session.execute(
                    select(StoreOrm.region_code, func.count())
                    .where(*live, open_year.in_(dong_years))
                    .group_by(StoreOrm.region_code)
                ).all()
            )
            dong_archive = {
                r: int(n)
                for r, n in session.execute(
                    select(S.region_code, func.sum(S.open_store_count))
                    .where(
                        S.service_industry_code == _ARCHIVE_CODE,
                        S.region_code.is_not(None),
                        archive_year.in_([str(y) for y in dong_years]),
                    )
                    .group_by(S.region_code)
                ).all()
            }
        return SurvivorBackcastData(survivors, archive, dong_survivors, dong_archive)
