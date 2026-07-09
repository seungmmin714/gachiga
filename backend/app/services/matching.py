"""매칭 엔진 v1 — 프레임워크 독립적인 순수 함수.

배치로 모인 대기 호출을 유사 출발지/목적지(하버사인 eps)와 시간 창 겹침으로
클러스터링하고, 우회 지수(Detour Index)가 임계값 이하인 2~3인 조합을
Total Utility(총 절감액) 기준으로 선택한다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations

from app.services.fare import estimate_fare, split_fare
from app.services.geo import ROAD_FACTOR, centroid, haversine_km

MIN_SOLO_KM = 1.0  # 이보다 짧은 이동은 동승 실익 없음


@dataclass(frozen=True)
class Candidate:
    request_id: int
    user_id: int
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    depart_after: datetime
    depart_before: datetime
    seats: int = 1
    origin_name: str = ""
    dest_name: str = ""


@dataclass
class MatchConfig:
    origin_eps_km: float = 0.8
    dest_eps_km: float = 0.8
    max_group: int = 3
    max_detour: float = 1.3
    min_overlap_min: float = 5.0


@dataclass
class ProposedGroup:
    candidates: list[Candidate]
    pickup_lat: float
    pickup_lng: float
    shared_km: float
    detour_index: float  # 멤버 중 최대 우회 지수
    total_fare: int
    shares: list[int] = field(default_factory=list)
    solo_fares: list[int] = field(default_factory=list)

    @property
    def total_utility(self) -> int:
        return sum(self.solo_fares) - self.total_fare

    def savings_ratio(self, i: int) -> float:
        if self.solo_fares[i] == 0:
            return 0.0
        return 1 - self.shares[i] / self.solo_fares[i]


def _overlap_minutes(a: Candidate, b: Candidate) -> float:
    start = max(a.depart_after, b.depart_after)
    end = min(a.depart_before, b.depart_before)
    return (end - start).total_seconds() / 60


def compatible(a: Candidate, b: Candidate, cfg: MatchConfig) -> bool:
    if a.user_id == b.user_id:
        return False
    if haversine_km(a.origin_lat, a.origin_lng, b.origin_lat, b.origin_lng) > cfg.origin_eps_km:
        return False
    if haversine_km(a.dest_lat, a.dest_lng, b.dest_lat, b.dest_lng) > cfg.dest_eps_km:
        return False
    return _overlap_minutes(a, b) >= cfg.min_overlap_min


def solo_km(c: Candidate) -> float:
    return haversine_km(c.origin_lat, c.origin_lng, c.dest_lat, c.dest_lng) * ROAD_FACTOR


def evaluate_group(cands: list[Candidate], cfg: MatchConfig) -> ProposedGroup | None:
    """조합의 우회 지수·요금을 계산하고 모두에게 이득일 때만 그룹을 반환."""
    if len(cands) < 2 or sum(c.seats for c in cands) > cfg.max_group:
        return None

    solo_kms = [solo_km(c) for c in cands]
    if any(km < MIN_SOLO_KM for km in solo_kms):
        return None

    o_lat, o_lng = centroid([(c.origin_lat, c.origin_lng) for c in cands])
    d_lat, d_lng = centroid([(c.dest_lat, c.dest_lng) for c in cands])

    # 통합 경로 근사: 중심 간 경로 + 각 멤버 픽업/하차 우회분
    pickup_detour = sum(haversine_km(c.origin_lat, c.origin_lng, o_lat, o_lng) for c in cands)
    drop_detour = sum(haversine_km(c.dest_lat, c.dest_lng, d_lat, d_lng) for c in cands)
    shared = (haversine_km(o_lat, o_lng, d_lat, d_lng) + pickup_detour + drop_detour) * ROAD_FACTOR

    detour = max(shared / km for km in solo_kms)
    if detour > cfg.max_detour:
        return None

    total_fare = estimate_fare(shared)
    solo_fares = [estimate_fare(km) for km in solo_kms]
    if total_fare >= sum(solo_fares):
        return None

    shares = split_fare(total_fare, solo_kms)
    if any(share >= solo for share, solo in zip(shares, solo_fares)):
        return None

    return ProposedGroup(
        candidates=list(cands),
        pickup_lat=o_lat,
        pickup_lng=o_lng,
        shared_km=shared,
        detour_index=detour,
        total_fare=total_fare,
        shares=shares,
        solo_fares=solo_fares,
    )


def build_groups(
    candidates: list[Candidate], cfg: MatchConfig | None = None
) -> list[ProposedGroup]:
    """대기 호출 목록에서 그리디하게 최적 그룹들을 구성한다.

    출발 시간이 이른 호출부터 시드로 잡고, 호환되는 이웃 중
    Total Utility가 가장 큰 3인 → 2인 조합 순으로 확정한다.
    """
    cfg = cfg or MatchConfig()
    pool = sorted(candidates, key=lambda c: c.depart_after)
    used: set[int] = set()
    groups: list[ProposedGroup] = []

    for seed in pool:
        if seed.request_id in used:
            continue
        partners = [
            c
            for c in pool
            if c.request_id != seed.request_id
            and c.request_id not in used
            and compatible(seed, c, cfg)
        ]
        if not partners:
            continue
        # 출발지가 가까운 순으로 상위 후보만 조합 탐색 (연산량 제한)
        partners.sort(
            key=lambda c: haversine_km(seed.origin_lat, seed.origin_lng, c.origin_lat, c.origin_lng)
        )
        partners = partners[:6]

        best: ProposedGroup | None = None
        for size in (2, 1):  # 시드 + 2인 → 시드 + 1인
            for combo in combinations(partners, size):
                if size == 2 and not compatible(combo[0], combo[1], cfg):
                    continue
                group = evaluate_group([seed, *combo], cfg)
                if group and (best is None or group.total_utility > best.total_utility):
                    best = group
            if best:
                break

        if best:
            groups.append(best)
            used.update(c.request_id for c in best.candidates)

    return groups
