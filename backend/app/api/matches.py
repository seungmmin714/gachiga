from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Match, User
from app.schemas.match import MatchMemberOut, MatchOut
from app.services import match_state

router = APIRouter(prefix="/matches", tags=["matches"])


def _get_match_for_member(db: Session, match_id: int, user: User) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "매칭을 찾을 수 없습니다")
    if not any(m.user_id == user.id for m in match.members):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "이 매칭의 멤버가 아닙니다")
    return match


def _to_out(match: Match) -> MatchOut:
    return MatchOut(
        id=match.id,
        status=match.status,
        pickup_name=match.pickup_name,
        pickup_lat=match.pickup_lat,
        pickup_lng=match.pickup_lng,
        estimated_fare_total=match.estimated_fare_total,
        detour_index=match.detour_index,
        created_at=match.created_at,
        confirmed_at=match.confirmed_at,
        members=[
            MatchMemberOut(
                user_id=m.user_id,
                name=m.user.name,
                ride_request_id=m.ride_request_id,
                share_amount=m.share_amount,
                solo_fare=m.solo_fare,
                accepted=m.accepted,
            )
            for m in match.members
        ],
    )


@router.get("/{match_id}", response_model=MatchOut)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _to_out(_get_match_for_member(db, match_id, current_user))


@router.post("/{match_id}/accept", response_model=MatchOut)
def accept_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = _get_match_for_member(db, match_id, current_user)
    if match.status != "proposed":
        raise HTTPException(status.HTTP_409_CONFLICT, "수락할 수 없는 상태입니다")
    member = match_state.get_member(db, match, current_user.id)
    return _to_out(match_state.accept(db, match, member))


@router.post("/{match_id}/reject", response_model=MatchOut)
def reject_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = _get_match_for_member(db, match_id, current_user)
    if match.status != "proposed":
        raise HTTPException(status.HTTP_409_CONFLICT, "거절할 수 없는 상태입니다")
    member = match_state.get_member(db, match, current_user.id)
    return _to_out(match_state.reject(db, match, member))


@router.post("/{match_id}/complete", response_model=MatchOut)
def complete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = _get_match_for_member(db, match_id, current_user)
    if match.status != "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, "확정된 매칭만 완료할 수 있습니다")
    return _to_out(match_state.complete(db, match))
