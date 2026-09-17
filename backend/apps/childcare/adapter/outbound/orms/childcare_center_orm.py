from datetime import date

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (store 전례)
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ChildcareCenterOrm(OrmBase):
    """어린이집 시설 — ERD 15테이블 밖 보조 테이블 (erd.md §2 어린이집 축).

    원천: 어린이집정보공개포털 cpmsapi030 × 자치구 25회 (폐지 시설은 반환하지 않음).
    store에 넣지 않는 근거: 원천이 폐지 시설을 빼고 주므로 인허가 개폐업 이력이 없다 —
    store에 섞으면 region_industry_metric 개폐업 지표가 오염된다(convenience 전례).
    §13 연결 원칙: district FK 필수(요청 arcode) + region FK nullable(좌표 공간조인 후 채움 —
    tobacco 전례)로 마스터 허브 연결. 시점별 정원·현원은 childcare_center_stat이 담당.
    """

    __tablename__ = "childcare_center"
    __table_args__ = (
        # 행정동별 운영 시설·소실 분석이 region_code + last_seen_on으로 조회한다
        Index("ix_childcare_center_region_last_seen", "region_code", "last_seen_on"),
    )

    center_id: Mapped[str] = mapped_column(primary_key=True)  # stcode
    name: Mapped[str]
    type_name: Mapped[str]  # 국공립/민간/가정/직장/법인·단체등/사회복지법인
    status_name: Mapped[str | None]  # 정상/재개/휴지 — 원천 공란 NULL 보존
    district_code: Mapped[str] = mapped_column(ForeignKey("district.district_code"))
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    address: Mapped[str]
    zipcode: Mapped[str | None]
    tel: Mapped[str | None]
    lat: Mapped[float | None]  # WGS84
    lng: Mapped[float | None]
    approved_on: Mapped[date | None]  # 인가일
    paused_from: Mapped[date | None]  # 휴지 시작
    paused_until: Mapped[date | None]  # 휴지 종료
    abolished_on: Mapped[date | None]  # 폐지일
    first_seen_on: Mapped[date]  # 최초 관측일
    last_seen_on: Mapped[date]  # 최근 관측일 — 정지 시 소실(폐원 추정 후보)
