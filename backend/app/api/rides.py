from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import RideRequest, User
from app.schemas.ride import RideCreate, RideOut

router = APIRouter(prefix="/rides", tags=["rides"])

ACTIVE_STATUSES = ("waiting", "proposed", "matched")


def _to_out(ride: RideRequest, match_id: int | None = None) -> RideOut:
    out = RideOut.model_validate(ride)
    out.match_id = match_id
    return out


def _active_match_id(db: Session, ride: RideRequest) -> int | None:
    """proposed/matched 상태 호출의 활성 매칭 id (Phase 3에서 매칭 테이블 생성 후 동작)."""
    if ride.status not in ("proposed", "matched"):
        return None
    try:
        from app.models.match import MatchMember
    except ImportError:
        return None
    member = db.scalar(
        select(MatchMember)
        .where(MatchMember.ride_request_id == ride.id)
        .order_by(MatchMember.id.desc())
    )
    return member.match_id if member else None


@router.post("", response_model=RideOut, status_code=status.HTTP_201_CREATED)
def create_ride(
    body: RideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active = db.scalar(
        select(RideRequest).where(
            RideRequest.user_id == current_user.id,
            RideRequest.status.in_(ACTIVE_STATUSES),
        )
    )
    if active:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 진행 중인 호출이 있습니다")

    ride = RideRequest(
        user_id=current_user.id,
        origin_name=body.origin_name,
        origin_lat=body.origin_lat,
        origin_lng=body.origin_lng,
        origin_point=f"SRID=4326;POINT({body.origin_lng} {body.origin_lat})",
        dest_name=body.dest_name,
        dest_lat=body.dest_lat,
        dest_lng=body.dest_lng,
        dest_point=f"SRID=4326;POINT({body.dest_lng} {body.dest_lat})",
        depart_after=body.depart_after,
        depart_before=body.depart_before,
        seats=body.seats,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return _to_out(ride)


@router.get("/me", response_model=list[RideOut])
def my_rides(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rides = db.scalars(
        select(RideRequest)
        .where(RideRequest.user_id == current_user.id)
        .order_by(RideRequest.created_at.desc())
    ).all()
    return [_to_out(r, _active_match_id(db, r)) for r in rides]


@router.delete("/{ride_id}", response_model=RideOut)
def cancel_ride(
    ride_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ride = db.get(RideRequest, ride_id)
    if ride is None or ride.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "호출을 찾을 수 없습니다")
    if ride.status not in ACTIVE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "취소할 수 없는 상태입니다")

    if ride.status in ("proposed", "matched"):
        from app.services.match_state import release_match_for_ride

        release_match_for_ride(db, ride)

    ride.status = "canceled"
    db.commit()
    db.refresh(ride)
    return _to_out(ride)
