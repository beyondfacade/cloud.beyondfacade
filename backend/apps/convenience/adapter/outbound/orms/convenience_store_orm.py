from datetime import date

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (store 전례)
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ConvenienceStoreOrm(OrmBase):
    """편의점 현행 스냅샷 — ERD 15테이블 밖 보조 테이블 (erd.md §2 편의점 축 2단계).

    원천: 소진공 상가정보 sdsc2 storeListInDong × 행정동 427 (indsSclsCd=G20405).
    store에 넣지 않는 근거: 상가정보는 개폐업 시계열 불가(api.md §2-3) — store에 섞으면
    region_industry_metric 개폐업 지표가 오염된다. 개폐업 이력은 tobacco_retailer 담당.
    §13 연결 원칙: region FK 필수(요청 행정동 — adongCd 프리픽스 유일 실측)로 허브 연결.
    관측 필드 first/last_seen_on — 스냅샷 소실(broker 전례) 기반 폐점 추정 후속 분석용.
    """

    __tablename__ = "convenience_store"
    __table_args__ = (
        # 경쟁밀도(행정동×최근 관측)·소실 분석이 region_code + last_seen_on으로 조회한다
        Index("ix_convenience_store_region_last_seen", "region_code", "last_seen_on"),
    )

    store_id: Mapped[str] = mapped_column(primary_key=True)  # bizesId 상가업소번호
    name: Mapped[str]  # bizesNm 상호명
    branch_name: Mapped[str | None]  # brchNm 지점명
    brand: Mapped[str | None]  # 상호 기반 추출 — 미확인 None (역정규화: 브랜드 분포 조회 축)
    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"))
    lat: Mapped[float | None]  # WGS84 (원천 제공)
    lng: Mapped[float | None]
    road_address: Mapped[str | None]
    jibun_address: Mapped[str | None]
    source_stdr_ym: Mapped[str]  # 원천 기준연월 (stdrYm)
    first_seen_on: Mapped[date]  # 최초 관측일 — 신규 출점(검증된 상권 프록시) 신호
    last_seen_on: Mapped[date]  # 최근 관측일 — 정지 시 소실(폐점 추정 후보)
