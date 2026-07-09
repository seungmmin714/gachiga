"""매칭 상태 전이 및 무산 처리."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Match, MatchMember, RideRequest


def get_member(db: Session, match: Match, user_id: int) -> MatchMember | None:
    return db.scalar(
        select(MatchMember).where(
            MatchMember.match_id == match.id, MatchMember.user_id == user_id
        )
    )


def accept(db: Session, match: Match, member: MatchMember) -> Match:
    member.accepted = True
    all_accepted = all(
        m.accepted is True
        for m in db.scalars(select(MatchMember).where(MatchMember.match_id == match.id))
    )
    if all_accepted:
        match.status = "confirmed"
        match.confirmed_at = datetime.now(timezone.utc)
        for m in match.members:
            m.ride_request.status = "matched"
    db.commit()
    db.refresh(match)
    return match


def reject(db: Session, match: Match, member: MatchMember) -> Match:
    """거절한 사용자의 호출은 취소, 나머지는 대기로 되돌려 재매칭."""
    member.accepted = False
    match.status = "canceled"
    for m in match.members:
        if m.id == member.id:
            m.ride_request.status = "canceled"
        else:
            m.ride_request.status = "waiting"
    db.commit()
    db.refresh(match)
    return match


def complete(db: Session, match: Match) -> Match:
    match.status = "completed"
    for m in match.members:
        m.ride_request.status = "completed"
    db.commit()
    db.refresh(match)
    return match


def release_match_for_ride(db: Session, ride: RideRequest) -> None:
    """호출 취소 시 소속 매칭을 무산시키고 다른 멤버를 대기로 되돌린다."""
    member = db.scalar(
        select(MatchMember)
        .join(Match)
        .where(
            MatchMember.ride_request_id == ride.id,
            Match.status.in_(("proposed", "confirmed")),
        )
    )
    if member is None:
        return
    match = member.match
    match.status = "canceled"
    for m in match.members:
        if m.ride_request_id != ride.id:
            m.ride_request.status = "waiting"
