from tests.test_matches_api import setup_proposed_match


def setup_completed_match(client, make_user):
    match_id, headers_a, headers_b = setup_proposed_match(client, make_user)
    client.post(f"/matches/{match_id}/accept", headers=headers_a)
    client.post(f"/matches/{match_id}/accept", headers=headers_b)
    client.post(f"/matches/{match_id}/complete", headers=headers_a)
    return match_id, headers_a, headers_b


def _other_member_id(client, match_id, headers, my_name):
    match = client.get(f"/matches/{match_id}", headers=headers).json()
    return next(m["user_id"] for m in match["members"] if m["name"] != my_name)


def test_review_updates_rating(client, make_user):
    match_id, headers_a, headers_b = setup_completed_match(client, make_user)
    reviewee_id = _other_member_id(client, match_id, headers_a, "가영")

    res = client.post(
        f"/matches/{match_id}/reviews",
        json={"reviewee_id": reviewee_id, "score": 5, "comment": "시간 약속을 잘 지켜요"},
        headers=headers_a,
    )
    assert res.status_code == 201, res.text

    me_b = client.get("/users/me", headers=headers_b).json()
    assert me_b["rating_avg"] == 5.0
    assert me_b["rating_count"] == 1


def test_review_duplicate_rejected(client, make_user):
    match_id, headers_a, _ = setup_completed_match(client, make_user)
    reviewee_id = _other_member_id(client, match_id, headers_a, "가영")
    body = {"reviewee_id": reviewee_id, "score": 4}
    assert (
        client.post(f"/matches/{match_id}/reviews", json=body, headers=headers_a).status_code
        == 201
    )
    assert (
        client.post(f"/matches/{match_id}/reviews", json=body, headers=headers_a).status_code
        == 409
    )


def test_review_requires_completed_match(client, make_user):
    match_id, headers_a, _ = setup_proposed_match(client, make_user)
    reviewee_id = _other_member_id(client, match_id, headers_a, "가영")
    res = client.post(
        f"/matches/{match_id}/reviews",
        json={"reviewee_id": reviewee_id, "score": 5},
        headers=headers_a,
    )
    assert res.status_code == 409


def test_review_self_rejected(client, make_user):
    match_id, headers_a, _ = setup_completed_match(client, make_user)
    match = client.get(f"/matches/{match_id}", headers=headers_a).json()
    my_id = next(m["user_id"] for m in match["members"] if m["name"] == "가영")
    res = client.post(
        f"/matches/{match_id}/reviews",
        json={"reviewee_id": my_id, "score": 5},
        headers=headers_a,
    )
    assert res.status_code == 400


def test_location_rest_roundtrip(client, make_user):
    match_id, headers_a, headers_b = setup_proposed_match(client, make_user)
    client.post(f"/matches/{match_id}/accept", headers=headers_a)
    client.post(f"/matches/{match_id}/accept", headers=headers_b)

    res = client.post(
        f"/matches/{match_id}/locations",
        json={"lat": 35.1755, "lng": 126.9050},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text

    res = client.get(f"/matches/{match_id}/locations", headers=headers_b)
    assert res.status_code == 200
    locations = res.json()
    assert len(locations) == 1
    assert abs(locations[0]["lat"] - 35.1755) < 1e-6


def test_location_requires_confirmed(client, make_user):
    match_id, headers_a, _ = setup_proposed_match(client, make_user)
    res = client.post(
        f"/matches/{match_id}/locations",
        json={"lat": 35.17, "lng": 126.9},
        headers=headers_a,
    )
    assert res.status_code == 409


def test_websocket_location_broadcast(client, make_user):
    match_id, headers_a, headers_b = setup_proposed_match(client, make_user)
    client.post(f"/matches/{match_id}/accept", headers=headers_a)
    client.post(f"/matches/{match_id}/accept", headers=headers_b)

    token_a = headers_a["Authorization"].removeprefix("Bearer ")
    token_b = headers_b["Authorization"].removeprefix("Bearer ")

    with client.websocket_connect(f"/ws/matches/{match_id}?token={token_a}") as ws_a:
        with client.websocket_connect(f"/ws/matches/{match_id}?token={token_b}") as ws_b:
            ws_a.send_json({"type": "location", "lat": 35.176, "lng": 126.906})
            received = ws_b.receive_json()
            assert received["type"] == "location"
            assert abs(received["lat"] - 35.176) < 1e-6


def test_websocket_rejects_non_member(client, make_user):
    match_id, _, _ = setup_proposed_match(client, make_user)
    headers_c, _ = make_user(email="outsider@jnu.ac.kr", name="외부인")
    token_c = headers_c["Authorization"].removeprefix("Bearer ")

    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/matches/{match_id}?token={token_c}"):
            pass
