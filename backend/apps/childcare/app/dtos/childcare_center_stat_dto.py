from dataclasses import dataclass
from datetime import date


@dataclass
class ChildcareRegionSummaryDto:
    region_code: str
    base_date: date | None
    center_count: int
    capacity: int
    child_count: int
    occupancy_rate: float | None
    waiting_count: int | None
