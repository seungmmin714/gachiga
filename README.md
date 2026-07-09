# 가치가 (GACHIGA)

광주 지역(전남대 ↔ 광주송정역 ↔ 유스퀘어) 이동 병목 구간에 특화된
**AI 경로 최적화 기반 택시 동승 매칭 서비스** — 1인 개발 MVP.

같은 방향 사용자를 배치 매칭으로 묶어 택시비를 인당 40~60% 절감한다.
성과 지표는 [REPORT.md](REPORT.md) 참고 (매칭 성공률 98.8%, 평균 절감 62.4%).

## 빠른 시작

```bash
cp .env.example .env          # 운영 시 JWT_SECRET_KEY 필히 변경
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.demo_seed   # 데모 데이터 (선택)
```

- API: http://localhost:8000 · Swagger: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

프론트엔드 (Node 20+):

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

데모 계정: `demo1@jnu.ac.kr` ~ `demo12@jnu.ac.kr` / `demo1234!`

## 테스트 · 린트

```bash
docker compose exec api pytest -v --cov=app   # 47건, 커버리지 92%
docker compose exec api ruff check .
```

시뮬레이션 검증(호출 500건: 성공률 ≥85%, 절감 ≥40%)은 `tests/test_simulation.py`에 포함.

## 아키텍처

```
gachiga/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 엔트리포인트 + 30초 배치 매칭 루프
│   │   ├── core/              # 설정, JWT/bcrypt, 전화번호 암호화, DB 세션
│   │   ├── models/            # users, ride_requests, matches, match_members, reviews
│   │   ├── schemas/           # Pydantic 요청/응답 (Swagger 자동 반영)
│   │   ├── api/               # auth, rides, matches, reviews/locations, health
│   │   ├── services/          # 매칭 엔진(순수 함수), 요금, 지오, 상태 전이, 위치 캐시
│   │   └── ws/                # WebSocket (위치 공유·매칭 알림)
│   ├── scripts/               # demo_seed
│   ├── tests/                 # PyTest (매칭 시뮬레이션 포함)
│   └── alembic/               # DB 마이그레이션
├── frontend/                  # Next.js (로그인 → 호출 → 매칭 → 완료/평점)
└── docker-compose.yml         # api + postgres(postgis) + redis
```

## 매칭 엔진 v1 요약

1. 30초 주기로 `waiting` 호출 수집 (만료 처리 포함)
2. 출발/도착 반경 0.8km + 시간 창 겹침 ≥5분 기준 호환 후보 클러스터링
3. 우회 지수(통합 경로 ÷ 단독 경로) ≤ 1.3 필터
4. Total Utility(총 절감액) 최대인 2~3인 조합 확정 → 전원 수락 시 매칭 확정
5. 거리 가중 요금 분담 (100원 단위, 총액 보존)

파라미터는 `.env`의 `MATCH_*`로 조정 가능.

## 주의

- 유상 합승 규제로 인해 MVP는 **비용 분담 기록/시뮬레이션**까지만 다룬다 (PG 결제 미연동).
- 지도는 API 키 없는 SVG 미니맵 — Kakao Maps 키 발급 후 교체 예정.
