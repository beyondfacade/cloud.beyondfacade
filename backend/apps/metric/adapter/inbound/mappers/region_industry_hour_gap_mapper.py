"""Inbound Boundary Gate — dto 목록 ↔ 응답 한 객체 (Router ↔ Interactor 경계)."""

from apps.metric.adapter.inbound.api.schemas.region_industry_hour_gap_schema import (
    HourGapBandResponse,
    RegionIndustryHourGapResponse,
)
from apps.metric.app.dtos.region_industry_hour_gap_dto import RegionIndustryHourGapDto


def to_response(bands: list[RegionIndustryHourGapDto]) -> RegionIndustryHourGapResponse:
    """빈 목록은 호출자가 먼저 걸러야 한다 — 머리 정보(동·업종·분기)를 첫 행에서 읽는다."""
    head = bands[0]
    return RegionIndustryHourGapResponse(
        region_code=head.region_code,
        industry_id=head.industry_id,
        year_quarter=head.year_quarter,
        bands=[
            HourGapBandResponse(
                hour_band=band.hour_band,
                footfall_intensity=band.footfall_intensity,
                sales_intensity=band.sales_intensity,
                gap=band.gap,
            )
            for band in bands
        ],
    )
