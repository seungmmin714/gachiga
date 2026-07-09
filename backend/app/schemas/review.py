from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    reviewee_id: int
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class ReviewOut(BaseModel):
    id: int
    match_id: int
    reviewer_id: int
    reviewee_id: int
    score: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class LocationOut(BaseModel):
    user_id: int
    lat: float
    lng: float
    recorded_at: datetime
