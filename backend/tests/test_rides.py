from datetime import datetime, timedelta, timezone

# 전남대 정문 / 광주송정역
JNU = {"name": "전남대 정문", "lat": 35.1760, "lng": 126.9059}
SONGJEONG = {"name": "광주송정역", "lat": 35.1372, "lng": 126.7935}


def ride_payload(minutes_from_now=30, window_min=30, seats=1):
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
        "seats": seats,
    }


def test_create_and_list_ride(client, make_user):
    headers, _ = make_user()
    res = client.post("/rides", json=ride_payload(), headers=headers)
    assert res.status_code == 201, res.text
    ride = res.json()
    assert ride["status"] == "waiting"
    assert ride["origin_name"] == "전남대 정문"

    res = client.get("/rides/me", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_duplicate_active_ride_rejected(client, make_user):
    headers, _ = make_user()
    assert client.post("/rides", json=ride_payload(), headers=headers).status_code == 201
    assert client.post("/rides", json=ride_payload(), headers=headers).status_code == 409


def test_cancel_ride(client, make_user):
    headers, _ = make_user()
    ride = client.post("/rides", json=ride_payload(), headers=headers).json()

    res = client.delete(f"/rides/{ride['id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "canceled"

    # 취소 후에는 새 호출 가능
    assert client.post("/rides", json=ride_payload(), headers=headers).status_code == 201


def test_cannot_cancel_others_ride(client, make_user):
    headers_a, _ = make_user(email="a@jnu.ac.kr")
    headers_b, _ = make_user(email="b@jnu.ac.kr")
    ride = client.post("/rides", json=ride_payload(), headers=headers_a).json()
    assert client.delete(f"/rides/{ride['id']}", headers=headers_b).status_code == 404


def test_invalid_time_window_rejected(client, make_user):
    headers, _ = make_user()
    payload = ride_payload()
    payload["depart_before"] = payload["depart_after"]
    assert client.post("/rides", json=payload, headers=headers).status_code == 422


def test_rides_require_auth(client):
    assert client.post("/rides", json=ride_payload()).status_code == 401
    assert client.get("/rides/me").status_code == 401
