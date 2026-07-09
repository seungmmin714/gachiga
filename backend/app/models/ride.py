from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# waiting -> proposed -> matched -> completed
#          \-> canceled / expired
RIDE_STATUSES = ("waiting", "proposed", "matched", "canceled", "expired", "completed")


class RideRequest(Base):
    __tablename__ = "ride_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    origin_name: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    origin_point = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)

    dest_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_point = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)

    depart_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    depart_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="waiting", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")
