from dataclasses import dataclass


@dataclass(frozen=True)
class RegionCommerceChange:
    """동별 상권 변화 지표 — 반복 그룹이 없어 유일하게 넓은 형태다 (설계서 §4-6).

    지표가 범주형(HH 정체 · HL 상권축소 · LH 상권확장 · LL 다이나믹)이라 숫자 값 컬럼에 담기지
    않는다. `change_name`은 `change_code`에 함수 종속이라 엄밀히는 3NF 위반이지만, 코드 4종의
    고정 매핑이라 룩업 테이블의 편익이 없고 원천이 두 컬럼을 같이 주므로 원본 보존 의미로
    유지한다(§13이 허용하는 근거 있는 부분적 역정규화).

    서울 평균 2컬럼은 행정동이 아니라 분기에만 의존하는 부분 함수 종속이라
    `seoul_commerce_change_baseline`으로 분리했다(설계서 §3-5).
    """

    adstrd_code: str
    year_quarter: str  # seoul_commerce_change_baseline FK — 분리된 테이블을 노드로 세운다
    change_code: str | None  # HH | HL | LH | LL
    change_name: str | None  # 정체 | 상권축소 | 상권확장 | 다이나믹
    operating_months: float | None  # 운영_영업_개월_평균
    closed_months: float | None  # 폐업_영업_개월_평균
    region_code: str | None
