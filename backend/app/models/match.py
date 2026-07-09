from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# proposed -> confirmed -> completed
#           \-> canceled
MATCH_STATUSES = ("proposed", "confirmed", "canceled", "completed")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True, nullable=False)

    pickup_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pickup_lat: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_lng: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_point = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)

    estimated_fare_total: Mapped[int] = mapped_column(Integer, nullable=False)
    detour_index: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    members = relationship("MatchMember", back_populates="match")


class MatchMember(Base):
    __tablename__ = "match_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True, nullable=False)
    ride_request_id: Mapped[int] = mapped_column(
        ForeignKey("ride_requests.id"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    share_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    solo_fare: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = 응답 대기
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    match = relationship("Match", back_populates="members")
    ride_request = relationship("RideRequest")
    user = relationship("User")
