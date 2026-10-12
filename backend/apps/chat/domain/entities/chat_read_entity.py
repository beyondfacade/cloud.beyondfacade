from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatRead:
    user_id: int
    room: str
    last_read_id: int
    updated_at: datetime
