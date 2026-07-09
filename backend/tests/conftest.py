import os

os.environ.setdefault("MATCHING_LOOP_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import engine
from app.main import app

TABLES = ["reviews", "match_members", "matches", "ride_requests", "users"]


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        existing = [
            t for t in TABLES if conn.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar()
        ]
        if existing:
            conn.execute(
                text(f"TRUNCATE TABLE {', '.join(existing)} RESTART IDENTITY CASCADE")
            )


@pytest.fixture()
def make_user(client):
    """회원가입 + 로그인 → (headers, user dict) 반환 헬퍼."""

    def _make(email="test@jnu.ac.kr", name="테스트", password="password123", phone=None):
        signup = client.post(
            "/auth/signup",
            json={
                "email": email,
                "password": password,
                "name": name,
                "department": "컴퓨터정보통신공학과",
                "phone": phone,
            },
        )
        assert signup.status_code == 201, signup.text
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        tokens = login.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        return headers, signup.json()

    return _make
