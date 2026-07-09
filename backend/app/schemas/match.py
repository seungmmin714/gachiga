from datetime import datetime

from pydantic import BaseModel


class MatchMemberOut(BaseModel):
    user_id: int
    name: str
    ride_request_id: int
    share_amount: int
    solo_fare: int
    accepted: bool | None

    model_config = {"from_attributes": True}


class MatchOut(BaseModel):
    id: int
    status: str
    pickup_name: str
    pickup_lat: float
    pickup_lng: float
    estimated_fare_total: int
    detour_index: float
    created_at: datetime
    confirmed_at: datetime | None
    members: list[MatchMemberOut]

    model_config = {"from_attributes": True}
