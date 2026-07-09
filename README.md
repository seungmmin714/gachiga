# GACHIGA (가치가)

광주 지역(전남대 ↔ 광주송정역 ↔ 유스퀘어) 택시 동승 매칭 서비스 — 1인 개발 MVP

## Phase 1: 프로젝트 셋업

FastAPI + PostgreSQL(PostGIS) + Redis 뼈대, Alembic 마이그레이션, 헬스체크 엔드포인트.

### 실행 방법

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- 헬스체크: http://localhost:8000/health

### 마이그레이션

컨테이너가 뜬 상태에서:

```bash
docker compose exec api alembic upgrade head
```

### 테스트

```bash
docker compose exec api pytest -v
```

## 구조

```
gachiga/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI 엔트리포인트
│   │   ├── core/          # 설정, DB 세션
│   │   ├── models/        # SQLAlchemy Base
│   │   └── api/           # 라우터 (health)
│   ├── tests/              # PyTest
│   └── alembic/            # DB 마이그레이션
└── docker-compose.yml       # api + postgres(postgis) + redis
```
