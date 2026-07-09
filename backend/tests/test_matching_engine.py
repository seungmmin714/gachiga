from datetime import datetime, timedelta, timezone

from app.services.matching import Candidate, MatchConfig, build_groups, evaluate_group

JNU = (35.1760, 126.9059)
SONGJEONG = (35.1372, 126.7935)
USQUARE = (35.1601, 126.8790)

BASE = datetime(2026, 7, 10, 16, 0, tzinfo=timezone.utc)


def cand(request_id, user_id, origin=JNU, dest=SONGJEONG, start_min=0, window_min=30, seats=1):
    after = BASE + timedelta(minutes=start_min)
    return Candidate(
        request_id=request_id,
        user_id=user_id,
        origin_lat=origin[0],
        origin_lng=origin[1],
        dest_lat=dest[0],
        dest_lng=dest[1],
        depart_after=after,
        depart_before=after + timedelta(minutes=window_min),
        seats=seats,
        origin_name="테스트 출발지",
        dest_name="테스트 목적지",
    )


def test_pair_same_corridor_matched():
    groups = build_groups([cand(1, 1), cand(2, 2)])
    assert len(groups) == 1
    group = groups[0]
    assert len(group.candidates) == 2
    assert group.detour_index <= 1.3
    # 두 사람 모두 비용 이득
    assert all(group.shares[i] < group.solo_fares[i] for i in range(2))


def test_three_person_group_preferred():
    groups = build_groups([cand(1, 1), cand(2, 2), cand(3, 3)])
    assert len(groups) == 1
    assert len(groups[0].candidates) == 3


def test_different_destinations_not_matched():
    groups = build_groups([cand(1, 1, dest=SONGJEONG), cand(2, 2, dest=USQUARE)])
    assert groups == []


def test_no_time_overlap_not_matched():
    groups = build_groups([cand(1, 1, start_min=0), cand(2, 2, start_min=120)])
    assert groups == []


def test_same_user_not_matched_with_self():
    groups = build_groups([cand(1, 7), cand(2, 7)])
    assert groups == []


def test_seats_capacity_respected():
    # 2인 파티 + 2인 파티 = 4석 > 최대 3석
    groups = build_groups([cand(1, 1, seats=2), cand(2, 2, seats=2)])
    assert groups == []


def test_detour_threshold_excludes_far_origin():
    far_origin = (JNU[0] + 0.02, JNU[1])  # 약 2.2km 밖 → eps 초과
    groups = build_groups([cand(1, 1), cand(2, 2, origin=far_origin)])
    assert groups == []


def test_evaluate_group_short_trip_rejected():
    near_dest = (JNU[0] + 0.005, JNU[1])  # 이동거리 1km 미만
    group = evaluate_group([cand(1, 1, dest=near_dest), cand(2, 2, dest=near_dest)], MatchConfig())
    assert group is None


def test_total_utility_positive():
    groups = build_groups([cand(1, 1), cand(2, 2)])
    assert groups[0].total_utility > 0
    assert sum(groups[0].shares) == groups[0].total_fare
