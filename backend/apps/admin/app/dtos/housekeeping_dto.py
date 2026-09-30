from dataclasses import dataclass


@dataclass(frozen=True)
class HousekeepingResultDto:
    access_events: int
    audit_entries: int
    sessions: int
    ip_blocks: int
