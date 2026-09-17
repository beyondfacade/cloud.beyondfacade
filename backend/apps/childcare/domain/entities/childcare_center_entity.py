from dataclasses import dataclass
from datetime import date

from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat


@dataclass(frozen=True)
class ChildcareCenter:
    """어린이집 1곳 — 어린이집정보공개포털 cpmsapi030(어린이집 기본정보) 현행 스냅샷.

    원천은 폐지 시설을 반환하지 않는다(서울 전량 상태 = 정상·재개·휴지·공란, 폐지일 채움 0 실측) —
    폐원은 응답 소실(last_seen_on 정지)로만 관측된다.
    연령별 반·아동·교직원 세부(CLASS/CHILD/EM_CNT_*)는 소비처가 생기면 age_band 행으로 추가(1NF).
    대표자명(CRREPNAME)은 가정 어린이집에서 개인 실명이라 수집하지 않는다.
    """

    center_id: str  # stcode 어린이집 코드 (종로 58건 유일 실측)
    name: str  # crname
    type_name: str  # crtypename 국공립/민간/가정/직장/법인·단체등/사회복지법인
    status_name: str | None  # crstatusname 정상/재개/휴지 — 공란 3건 실측(현원 0) None 보존
    district_code: str  # 요청 arcode = district_code 5자리
    address: str  # craddr
    zipcode: str | None
    tel: str | None  # crtelno
    lat: float | None  # la WGS84 (종로·강남 채움 100% — 결측 방어)
    lng: float | None  # lo
    approved_on: date | None  # crcnfmdt 인가일
    paused_from: date | None  # crpausebegindt 휴지 시작
    paused_until: date | None  # crpauseenddt 휴지 종료
    abolished_on: date | None  # crabldt 폐지일
    stat: ChildcareCenterStat
