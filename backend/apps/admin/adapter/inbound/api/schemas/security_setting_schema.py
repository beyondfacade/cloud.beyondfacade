from datetime import datetime

from pydantic import BaseModel


class AutoDefenseUpdateRequest(BaseModel):
    enabled: bool


class AutoBlockRuleResponse(BaseModel):
    rule: str
    title: str
    threshold: int
    window_minutes: int
    block_minutes: int
    repeat_block_minutes: int


class AutoDefenseResponse(BaseModel):
    enabled: bool
    updated_at: datetime | None
    updated_by: str | None
    rules: list[AutoBlockRuleResponse]
