"""매칭 엔진 시뮬레이션 검증 (PRD §10).

전남대·광주송정역·유스퀘어 좌표 기반 가상 호출 500건을 생성해
매칭 성공률 ≥ 85%, 인당 평균 비용 절감률 ≥ 40%를 검증한다.
"""

import random
import time
from datetime import datetime, timedelta, timezone

from app.services.matching import Candidate, build_groups

HUBS = {
    "전남대 정문": (35.1760, 126.9059),
    "광주송정역": (35.1372, 126.7935),
    "유스퀘어": (35.1601, 126.8790),
}
CORRIDORS = [
    ("전남대 정문", "광주송정역"),
    ("광주송정역", "전남대 정문"),
    ("전남대 정문", "유스퀘어"),
    ("유스퀘어", "전남대 정문"),
]

N_REQUESTS = 500
JITTER_DEG = 0.003  # 약 ±330m — 같은 정류 지점 인근에서 출발/도착
BASE = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)  # 15:00~19:00 피크


def generate_candidates(n=N_REQUESTS, seed=42) -> list[Candidate]:
    rng = random.Random(seed)
    candidates = []
    for i in range(1, n + 1):
        origin_name, dest_name = rng.choice(CORRIDORS)
        o_lat, o_lng = HUBS[origin_name]
        d_lat, d_lng = HUBS[dest_name]
        after = BASE + timedelta(minutes=rng.uniform(0, 240))
        window = rng.uniform(30, 60)
        candidates.append(
            Candidate(
                request_id=i,
                user_id=i,
                origin_lat=o_lat + rng.uniform(-JITTER_DEG, JITTER_DEG),
                origin_lng=o_lng + rng.uniform(-JITTER_DEG, JITTER_DEG),
                dest_lat=d_lat + rng.uniform(-JITTER_DEG, JITTER_DEG),
                dest_lng=d_lng + rng.uniform(-JITTER_DEG, JITTER_DEG),
                depart_after=after,
                depart_before=after + timedelta(minutes=window),
                seats=1,
                origin_name=origin_name,
                dest_name=dest_name,
            )
        )
    return candidates


def run_simulation(n=N_REQUESTS, seed=42):
    candidates = generate_candidates(n, seed)
    start = time.perf_counter()
    groups = build_groups(candidates)
    elapsed = time.perf_counter() - start

    matched = sum(len(g.candidates) for g in groups)
    savings = [g.savings_ratio(i) for g in groups for i in range(len(g.candidates))]
    return {
        "total": n,
        "matched": matched,
        "success_rate": matched / n,
        "avg_savings": sum(savings) / len(savings) if savings else 0.0,
        "groups": len(groups),
        "avg_detour": sum(g.detour_index for g in groups) / len(groups) if groups else 0.0,
        "elapsed_sec": elapsed,
    }


def test_simulation_success_rate_and_savings():
    result = run_simulation()
    assert result["success_rate"] >= 0.85, f"매칭 성공률 미달: {result['success_rate']:.1%}"
    assert result["avg_savings"] >= 0.40, f"평균 절감률 미달: {result['avg_savings']:.1%}"
    assert result["avg_detour"] <= 1.3


def test_simulation_batch_latency():
    result = run_simulation()
    assert result["elapsed_sec"] < 2.0, f"배치 매칭 지연 과다: {result['elapsed_sec']:.2f}s"


def test_simulation_stable_across_seeds():
    for seed in (1, 7, 2026):
        result = run_simulation(seed=seed)
        assert result["success_rate"] >= 0.85
        assert result["avg_savings"] >= 0.40
