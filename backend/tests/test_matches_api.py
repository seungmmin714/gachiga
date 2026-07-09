from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.services.match_runner import run_batch_matching

JNU = {"name": "전남대 정문", "lat": 35.1760, "lng": 126.9059}
SONGJEONG = {"name": "광주송정역", "lat": 35.1372, "lng": 126.7935}


def ride_payload(minutes_from_now=30, window_min=40):
    after = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    return {
        "origin_name": JNU["name"],
        "origin_lat": JNU["lat"],
        "origin_lng": JNU["lng"],
        "dest_name": SONGJEONG["name"],
        "dest_lat": SONGJEONG["lat"],
        "dest_lng": SONGJEONG["lng"],
        "depart_after": after.isoformat(),
        "depart_before": (after + timedelta(minutes=window_min)).isoformat(),
        "seats": 1,
    }


def setup_proposed_match(client, make_user):
    headers_a, user_a = make_user(email="a@jnu.ac.kr", name="가영")
    headers_b, user_b = make_user(email="b@jnu.ac.kr", name="나영")
    client.post("/rides", json=ride_payload(), headers=headers_a)
    client.post("/rides", json=ride_payload(), headers=headers_b)

    with SessionLocal() as db:
        summaries = run_batch_matching(db)
    assert len(summaries) == 1
    return summaries[0]["match_id"], headers_a, headers_b


def test_batch_matching_creates_proposal(client, make_user):
    match_id, headers_a, _ = setup_proposed_match(client, make_user)

    res = client.get(f"/matches/{match_id}", headers=headers_a)
    assert res.status_code == 200
    match = res.json()
    assert match["status"] == "proposed"
    assert len(match["members"]) == 2
    assert sum(m["share_amount"] for m in match["members"]) == match["estimated_fare_total"]
    assert match["detour_index"] <= 1.3

    # 내 호출 목록에 match_id 노출
    rides = client.get("/rides/me", headers=headers_a).json()
    assert rides[0]["status"] == "proposed"
    assert rides[0]["match_id"] == match_id


def test_accept_flow_confirms_match(client, make_user):
    match_id, headers_a, headers_b = setup_proposed_match(client, make_user)

    res = client.post(f"/matches/{match_id}/accept", headers=headers_a)
    assert res.json()["status"] == "proposed"  # 한 명만 수락한 상태

    res = client.post(f"/matches/{match_id}/accept", headers=headers_b)
    assert res.json()["status"] == "confirmed"

    rides = client.get("/rides/me", headers=headers_a).json()
    assert rides[0]["status"] == "matched"

    # 확정 후 완료 처리
    res = client.post(f"/matches/{match_id}/complete", headers=headers_a)
    assert res.json()["status"] == "completed"
    rides = client.get("/rides/me", headers=headers_a).json()
    assert rides[0]["status"] == "completed"


def test_reject_cancels_and_requeues_others(client, make_user):
    match_id, headers_a, headers_b = setup_proposed_match(client, make_user)

    res = client.post(f"/matches/{match_id}/reject", headers=headers_a)
    assert res.json()["status"] == "canceled"

    # 거절자는 canceled, 상대는 waiting으로 복귀
    assert client.get("/rides/me", headers=headers_a).json()[0]["status"] == "canceled"
    assert client.get("/rides/me", headers=headers_b).json()[0]["status"] == "waiting"


def test_ride_cancel_releases_match(client, make_user):
    match_id, headers_a, headers_b = setup_proposed_match(client, make_user)

    ride_a = client.get("/rides/me", headers=headers_a).json()[0]
    res = client.delete(f"/rides/{ride_a['id']}", headers=headers_a)
    assert res.status_code == 200

    assert client.get("/rides/me", headers=headers_b).json()[0]["status"] == "waiting"
    res = client.get(f"/matches/{match_id}", headers=headers_b)
    assert res.json()["status"] == "canceled"


def test_non_member_cannot_access_match(client, make_user):
    match_id, _, _ = setup_proposed_match(client, make_user)
    headers_c, _ = make_user(email="c@jnu.ac.kr", name="다영")
    assert client.get(f"/matches/{match_id}", headers=headers_c).status_code == 403


def test_complete_requires_confirmed(client, make_user):
    match_id, headers_a, _ = setup_proposed_match(client, make_user)
    assert client.post(f"/matches/{match_id}/complete", headers=headers_a).status_code == 409


def test_expired_rides_are_marked(client, make_user):
    headers, _ = make_user(email="exp@jnu.ac.kr")
    payload = ride_payload(minutes_from_now=-120, window_min=30)  # 이미 지난 시간대
    res = client.post("/rides", json=payload, headers=headers)
    assert res.status_code == 201

    with SessionLocal() as db:
        run_batch_matching(db)

    assert client.get("/rides/me", headers=headers).json()[0]["status"] == "expired"
