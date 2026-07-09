def test_signup_login_me(client, make_user):
    headers, user = make_user(email="kim@jnu.ac.kr", name="김전남", phone="010-1234-5678")
    assert user["email"] == "kim@jnu.ac.kr"

    res = client.get("/users/me", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "김전남"
    assert body["phone"] == "010-1234-5678"  # 암호화 저장 후 복호화 확인


def test_signup_duplicate_email(client, make_user):
    make_user(email="dup@jnu.ac.kr")
    res = client.post(
        "/auth/signup",
        json={"email": "dup@jnu.ac.kr", "password": "password123", "name": "중복"},
    )
    assert res.status_code == 409


def test_login_wrong_password(client, make_user):
    make_user(email="pw@jnu.ac.kr")
    res = client.post("/auth/login", json={"email": "pw@jnu.ac.kr", "password": "wrongpass1"})
    assert res.status_code == 401


def test_refresh_token(client, make_user):
    make_user(email="rt@jnu.ac.kr")
    login = client.post("/auth/login", json={"email": "rt@jnu.ac.kr", "password": "password123"})
    refresh_token = login.json()["refresh_token"]

    res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert "access_token" in res.json()

    # access 토큰을 refresh 자리에 쓰면 거부
    access_token = login.json()["access_token"]
    res = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert res.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/users/me").status_code == 401
    res = client.get("/users/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401


def test_password_stored_hashed(client, make_user):
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models import User

    make_user(email="hash@jnu.ac.kr", password="plainpassword1")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "hash@jnu.ac.kr"))
        assert user.password_hash != "plainpassword1"
        assert user.password_hash.startswith("$2")
