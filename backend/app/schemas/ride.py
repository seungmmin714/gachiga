from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator


class RideCreate(BaseModel):
    origin_name: str = Field(min_length=1, max_length=100)
    origin_lat: float = Field(ge=-90, le=90)
    origin_lng: float = Field(ge=-180, le=180)
    dest_name: str = Field(min_length=1, max_length=100)
    dest_lat: float = Field(ge=-90, le=90)
    dest_lng: float = Field(ge=-180, le=180)
    depart_after: datetime
    depart_before: datetime
    seats: int = Field(default=1, ge=1, le=3)

    @field_validator("depart_after", "depart_before")
    @classmethod
    def ensure_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode="after")
    def check_window(self):
        if self.depart_before <= self.depart_after:
            raise ValueError("depart_before는 depart_after보다 이후여야 합니다")
        return self


class RideOut(BaseModel):
    id: int
    origin_name: str
    origin_lat: float
    origin_lng: float
    dest_name: str
    dest_lat: float
    dest_lng: float
    depart_after: datetime
    depart_before: datetime
    seats: int
    status: str
    created_at: datetime
    match_id: int | None = None

    model_config = {"from_attributes": True}
