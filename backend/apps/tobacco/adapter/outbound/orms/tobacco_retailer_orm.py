from datetime import date, datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (store 전례)
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class TobaccoRetailerOrm(OrmBase):
    """담배소매인 지정 현황 — ERD 15테이블 밖 보조 테이블 (erd.md §2.1 참조).

    편의점은 LOCALDATA 단일 인허가 코드가 없어(brainstorming §3.5) 담배소매인
    지정(지자체 거리 제한)이 사실상 출점 가능 여부를 결정한다.
    §13 연결 원칙: district FK(필수) + region FK(공간조인 후 채움, nullable)로
    마스터 허브에 연결 — 고립 없음. 좌표는 EPSG:5174→WGS84 변환값 (store 전례).
    """

    __tablename__ = "tobacco_retailer"
    __table_args__ = (
        # 출점 가능성 분석이 행정동×영업상태로 밀도를 조회한다
        Index("ix_tobacco_retailer_region_status", "region_code", "status_code"),
    )

    retailer_id: Mapped[str] = mapped_column(primary_key=True)  # 관리번호 (유일 실측)
    name: Mapped[str]
    district_code: Mapped[str] = mapped_column(ForeignKey("district.district_code"))
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    status_code: Mapped[str]  # 상세영업상태코드 (0 정상영업 ~ 6 영업정지)
    status_name: Mapped[str]
    designated_date: Mapped[date | None]  # 지정일자
    permit_date: Mapped[date | None]  # 인허가일자
    close_date: Mapped[date | None]  # 폐업일자
    cancel_date: Mapped[date | None]  # 인허가취소일자 (지정취소·직권취소 폐지 시점)
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    road_address: Mapped[str | None]
    jibun_address: Mapped[str | None]
    source_updated_at: Mapped[datetime]
