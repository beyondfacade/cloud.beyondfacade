from pydantic import BaseModel


class ChatReadRequest(BaseModel):
    last_read_id: int


class ChatReadResponse(BaseModel):
    room: str
    last_read_id: int
