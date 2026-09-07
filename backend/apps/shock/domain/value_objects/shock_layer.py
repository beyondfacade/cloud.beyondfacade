"""특이변수(외생 충격) 공통 VO — 4계층 분류·업종 영향도 (brainstorming §5.2).

계층·영향도는 문자열 상수(StrEnum)로 고정한다 — if 분기 대신 값 자체가 의미를 안다.
"""

from enum import StrEnum


class ShockLayer(StrEnum):
    """충격 4계층 — 반복 발생하는 충격을 같은 프레임으로 흡수한다 (brainstorming §5.2)."""

    POLICY = "policy"  # ① 정책·규제 (시행일 명확 — 시계열 더미 변수)
    MACRO = "macro"  # ② 거시경제 (금리·물가·환율)
    TREND = "trend"  # ③ 사회·트렌드 (뉴스 언급량이 주 센서)
    REGIONAL = "regional"  # ④ 지역 이벤트 (상권 단위 — shock_event_region 연결)


class Severity(StrEnum):
    """업종 영향도 등급 — shock_event_industry.severity."""

    CRITICAL = "critical"  # 집합금지·영업중단 수준
    HIGH = "high"  # 강한 영업제한 (시간·취식 제한 등)
    MEDIUM = "medium"  # 유의미한 간접 영향
    LOW = "low"  # 경미한 영향
