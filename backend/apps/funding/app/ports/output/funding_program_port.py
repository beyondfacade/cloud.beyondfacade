"""Driven Ports — funding_program이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import date

from apps.funding.app.dtos.funding_program_dto import RateDto
from apps.funding.domain.entities.funding_program_entity import FundingProgram


class FundingProgramRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, programs: list[FundingProgram]) -> tuple[int, int]:
        """program_id 기준 업서트(멱등) — (신규, 갱신) 건수 반환."""

    @abstractmethod
    def refresh_expirations(self, today: date) -> int:
        """deadline < today → is_expired=True, 연장된 공고는 복원 — 신규 만료 건수 반환."""

    @abstractmethod
    def list_open(self, limit: int) -> list[FundingProgram]:
        """미만료 공고 마감일 오름차순(상시=NULL은 뒤) limit건."""

    @abstractmethod
    def list_open_all(self) -> list[FundingProgram]:
        """미만료 공고 전량 — 후보 선별이 도메인에서 필터·정렬하므로 자르지 않고 받는다."""


class FundingSearchGatewayPort(ABC):
    @abstractmethod
    def fetch_all(self) -> list[FundingProgram]:
        """원천 API에서 전체 공고를 수신해 엔티티로 반환한다."""


class SeoulDistrictNamesPort(ABC):
    """서울 자치구 이름 — 지자체 소관 공고 판정에 쓴다 (하드코딩하면 마스터와 어긋난다)."""

    @abstractmethod
    def names(self) -> frozenset[str]:
        """`district` 마스터의 서울 자치구 25개 이름."""


class DistrictNameLookupPort(ABC):
    """자치구 코드(행정동 코드 앞 5자리) → 이름."""

    @abstractmethod
    def name_of(self, district_code: str) -> str | None:
        """모르는 코드면 None."""


class LatestRatesPort(ABC):
    """지원 정보 화면의 금리 참고값 — 기준금리·시설자금대출 금리 최신월."""

    @abstractmethod
    def latest(self) -> list[RateDto]:
        """계열마다 최신 1건. 적재 전이면 빈 목록."""
