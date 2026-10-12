from dataclasses import dataclass


@dataclass(frozen=True)
class ChatReadDto:
    room: str
    last_read_id: int
