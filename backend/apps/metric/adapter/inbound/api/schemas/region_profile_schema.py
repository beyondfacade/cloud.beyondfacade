from pydantic import BaseModel


class RegionProfileResponse(BaseModel):
    """동네 프로필 응답 — 판정과 근거 수치를 함께 준다 (프론트엔드 계약).

    `neighborhood_type`·`time_label`·`peak_block`·`trough_block`은 **코드**다. 화면에 띄울 이름·
    괄호 설명·툴팁·서사 문구는 프론트엔드가 갖는다(`industryLabel` 전례). `type_reason`만 예외로
    한국어인데, 실제로 넘은 수치가 박힌 문장이라 표현이 아니라 데이터이기 때문이다.
    """

    region_code: str
    year_quarter: str
    neighborhood_type: str  # office | campus | dining | hub | residential | mixed
    type_reason: str
    time_label: str | None  # morning | day | evening | night | flat
    peak_block: str | None  # morning | day | evening | night
    trough_block: str | None
    worker_resident_ratio: float | None  # 직장인구 결측 11개 동은 null
    weekend_index: float | None
    night_index: float | None
    footfall_20s_share: float | None
    fnb_share: float | None
    facility_total: int | None
    resident_total: int | None


class ProfileMetricValueResponse(BaseModel):
    """단계구분도 응답 단위 — `/metrics`·`/commerce-changes`와 같은 {region_code, value} 계약."""

    region_code: str
    value: float
