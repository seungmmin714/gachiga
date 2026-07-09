"""데모 시나리오 시드 — Faker로 가상 사용자·호출을 만들고 배치 매칭을 1회 실행.

사용법: docker compose exec api python -m scripts.demo_seed
"""

import random
from datetime import datetime, timedelta, timezone

from faker import Faker

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import RideRequest, User
from app.services.match_runner import run_batch_matching

HUBS = {
    "전남대 정문": (35.1760, 126.9059),
    "광주송정역": (35.1372, 126.7935),
    "유스퀘어": (35.1601, 126.8790),
}
CORRIDORS = [
    ("전남대 정문", "광주송정역"),
    ("전남대 정문", "유스퀘어"),
    ("광주송정역", "전남대 정문"),
]
DEPARTMENTS = ["컴퓨터정보통신공학과", "경영학부", "간호학과", "기계공학부", "심리학과"]

N_USERS = 12


def seed():
    fake = Faker("ko_KR")
    rng = random.Random(2026)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        users = []
        for i in range(1, N_USERS + 1):
            email = f"demo{i}@jnu.ac.kr"
            if db.query(User).filter(User.email == email).first():
                print(f"이미 시드됨: {email} — 건너뜀")
                continue
            user = User(
                email=email,
                password_hash=hash_password("demo1234!"),
                name=fake.name(),
                department=rng.choice(DEPARTMENTS),
            )
            db.add(user)
            users.append(user)
        db.flush()

        for user in users:
            origin_name, dest_name = rng.choice(CORRIDORS)
            o_lat, o_lng = HUBS[origin_name]
            d_lat, d_lng = HUBS[dest_name]
            jitter = lambda: rng.uniform(-0.002, 0.002)  # noqa: E731
            after = now + timedelta(minutes=rng.uniform(5, 30))
            db.add(
                RideRequest(
                    user_id=user.id,
                    origin_name=origin_name,
                    origin_lat=o_lat + jitter(),
                    origin_lng=o_lng + jitter(),
                    dest_name=dest_name,
                    dest_lat=d_lat + jitter(),
                    dest_lng=d_lng + jitter(),
                    depart_after=after,
                    depart_before=after + timedelta(minutes=40),
                    seats=1,
                )
            )
        db.commit()
        print(f"사용자 {len(users)}명, 호출 {len(users)}건 시드 완료 (비밀번호: demo1234!)")

        summaries = run_batch_matching(db)
        print(f"배치 매칭 실행 → 매칭 {len(summaries)}건 생성")
        for s in summaries:
            print(f"  - 매칭 #{s['match_id']}: 사용자 {s['user_ids']}")


if __name__ == "__main__":
    seed()
