from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Match, Review, User
from app.schemas.review import LocationIn, LocationOut, ReviewCreate, ReviewOut
from app.services.locations import get_locations, save_location
from app.ws.manager import manager

router = APIRouter(prefix="/matches", tags=["reviews", "locations"])


def _member_match(db: Session, match_id: int, user: User) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "매칭을 찾을 수 없습니다")
    if not any(m.user_id == user.id for m in match.members):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "이 매칭의 멤버가 아닙니다")
    return match


@router.post("/{match_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    match_id: int,
    body: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = _member_match(db, match_id, current_user)
    if match.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "완료된 매칭만 평가할 수 있습니다")
    if body.reviewee_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "자기 자신은 평가할 수 없습니다")
    if not any(m.user_id == body.reviewee_id for m in match.members):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "동승 멤버만 평가할 수 있습니다")
    duplicate = db.scalar(
        select(Review).where(
            Review.match_id == match_id,
            Review.reviewer_id == current_user.id,
            Review.reviewee_id == body.reviewee_id,
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 평가했습니다")

    review = Review(
        match_id=match_id,
        reviewer_id=current_user.id,
        reviewee_id=body.reviewee_id,
        score=body.score,
        comment=body.comment,
    )
    db.add(review)

    # 평판 지수 갱신 (누적 평균)
    reviewee = db.get(User, body.reviewee_id)
    reviewee.rating_avg = (
        reviewee.rating_avg * reviewee.rating_count + body.score
    ) / (reviewee.rating_count + 1)
    reviewee.rating_count += 1

    db.commit()
    db.refresh(review)
    return review


@router.post("/{match_id}/locations", response_model=LocationOut)
async def update_location(
    match_id: int,
    body: LocationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """위치 갱신 REST 폴백 (WebSocket 미사용 클라이언트용)."""
    match = _member_match(db, match_id, current_user)
    if match.status not in ("confirmed", "completed"):
        raise HTTPException(status.HTTP_409_CONFLICT, "확정된 매칭에서만 위치를 공유합니다")
    payload = save_location(match_id, current_user.id, body.lat, body.lng)
    await manager.broadcast_match(match_id, payload)
    return payload


@router.get("/{match_id}/locations", response_model=list[LocationOut])
def list_locations(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = _member_match(db, match_id, current_user)
    return get_locations(match_id, [m.user_id for m in match.members])
