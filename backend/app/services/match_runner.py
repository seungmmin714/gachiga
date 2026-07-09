"""배치 매칭 실행기 — 대기 호출을 모아 매칭 엔진을 돌리고 결과를 저장한다."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Match, MatchMember, RideRequest
from app.services.matching import Candidate, MatchConfig, build_groups

logger = logging.getLogger(__name__)


def config_from_settings() -> MatchConfig:
    return MatchConfig(
        origin_eps_km=settings.MATCH_ORIGIN_EPS_KM,
        dest_eps_km=settings.MATCH_DEST_EPS_KM,
        max_group=settings.MATCH_MAX_GROUP,
        max_detour=settings.MATCH_MAX_DETOUR,
        min_overlap_min=settings.MATCH_MIN_OVERLAP_MIN,
    )


def run_batch_matching(db: Session) -> list[dict]:
    """만료 처리 후 대기 호출을 매칭. 생성된 매칭 요약 목록을 반환."""
    now = datetime.now(timezone.utc)

    expired = db.scalars(
        select(RideRequest).where(
            RideRequest.status == "waiting", RideRequest.depart_before < now
        )
    ).all()
    for r in expired:
        r.status = "expired"

    waiting = db.scalars(select(RideRequest).where(RideRequest.status == "waiting")).all()
    candidates = [
        Candidate(
            request_id=r.id,
            user_id=r.user_id,
            origin_lat=r.origin_lat,
            origin_lng=r.origin_lng,
            dest_lat=r.dest_lat,
            dest_lng=r.dest_lng,
            depart_after=r.depart_after,
            depart_before=r.depart_before,
            seats=r.seats,
            origin_name=r.origin_name,
            dest_name=r.dest_name,
        )
        for r in waiting
    ]

    groups = build_groups(candidates, config_from_settings())
    rides_by_id = {r.id: r for r in waiting}
    summaries: list[dict] = []

    for group in groups:
        match = Match(
            status="proposed",
            pickup_name=f"{group.candidates[0].origin_name} 인근",
            pickup_lat=group.pickup_lat,
            pickup_lng=group.pickup_lng,
            pickup_point=f"SRID=4326;POINT({group.pickup_lng} {group.pickup_lat})",
            estimated_fare_total=group.total_fare,
            detour_index=round(group.detour_index, 3),
        )
        db.add(match)
        db.flush()
        for cand, share, solo in zip(group.candidates, group.shares, group.solo_fares):
            db.add(
                MatchMember(
                    match_id=match.id,
                    ride_request_id=cand.request_id,
                    user_id=cand.user_id,
                    share_amount=share,
                    solo_fare=solo,
                )
            )
            rides_by_id[cand.request_id].status = "proposed"
        summaries.append(
            {"match_id": match.id, "user_ids": [c.user_id for c in group.candidates]}
        )

    db.commit()
    if summaries or expired:
        logger.info("배치 매칭: %d건 생성, %d건 만료", len(summaries), len(expired))
    return summaries
