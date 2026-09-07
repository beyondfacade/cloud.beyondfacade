from pydantic import BaseModel


class RegionResponse(BaseModel):
    region_code: str
    name: str
