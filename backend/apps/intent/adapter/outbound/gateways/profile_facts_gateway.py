"""Driven Adapter — metric BC의 파생 지표를 진단 재료로 (cross-BC는 유스케이스 경유, 여기서만)."""

from apps.intent.app.ports.output.intent_port import ProfileFactsPort
from apps.intent.domain.services.diagnosis import PeakSalesBand, ProfileFacts
from apps.metric.dependencies.region_profile_dependencies import (
    get_region_industry_hour_gap_use_case,
    get_region_profile_use_case,
)


class ProfileFactsGateway(ProfileFactsPort):
    def latest_profile(self, region_code: str, region_name: str) -> ProfileFacts | None:
        dto = get_region_profile_use_case().find_latest(region_code)
        if dto is None:
            return None
        return ProfileFacts(
            region_name=region_name,
            type_code=dto.neighborhood_type,
            type_reason=dto.type_reason,
            time_label=dto.time_label,
            year_quarter=dto.year_quarter,
        )

    def peak_sales_band(self, region_code: str, industry_id: str) -> PeakSalesBand | None:
        bands = get_region_industry_hour_gap_use_case().list_latest_bands(region_code, industry_id)
        if not bands:
            return None
        # 정점은 gap이 아니라 매출 강도다 — 어긋남의 부호는 상대 순위에 있다 (v0.26.0 검증)
        peak = max(bands, key=lambda b: b.sales_intensity)
        return PeakSalesBand(hour_band=peak.hour_band, year_quarter=peak.year_quarter)
