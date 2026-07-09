# 가치가 (GACHIGA) — MVP 성과 리포트

2026-07-10 기준, PRD Phase 1~6 완료.

## PRD 목표 대비 달성치

| 지표 | 목표 | 달성 | 검증 방법 |
| --- | --- | --- | --- |
| 매칭 성공률 (시뮬레이션) | 85% 이상 | **98.8%** | 가상 호출 500건 × 시드 3종 (`tests/test_simulation.py`) |
| 동승 시 인당 비용 절감률 | 40% 이상 | **62.4% (평균)** | 시뮬레이션 매칭 그룹 분담액 vs 단독 요금 |
| 배치 매칭 처리 시간 | (참고) API p95 200ms | **500건 65ms** | `build_groups` 순수 함수 벤치마크 |
| 핵심 로직 테스트 커버리지 | 80% 이상 | **92% (전체)** — 매칭·정산 95~100% | `pytest --cov=app` (47건 통과) |
| 평균 우회 지수 | ≤ 1.3 (임계값) | **1.157** | 시뮬레이션 그룹 평균 |

## 시뮬레이션 조건

- 거점: 전남대 정문 ↔ 광주송정역 ↔ 유스퀘어 (±330m 지터)
- 시간대: 15:00~19:00 피크, 출발 대기창 30~60분
- 매칭 규칙: 출발/도착 반경 0.8km, 시간 겹침 ≥5분, 2~3인, 우회 지수 ≤1.3, 전원 비용 이득 조건

## 요금 모델 (추정)

기본요금 4,800원(2km) + km당 850원, 100원 단위 반올림.
전남대→송정역 단독 약 16,400원 → 2인 동승 시 인당 약 8,700원(약 47% 절감), 3인 시 약 60% 절감.
분담액은 이동 거리 가중 배분, 합계가 총액과 정확히 일치(100원 단위).

## 구현 범위

- **Phase 1** 인프라: FastAPI + PostgreSQL(PostGIS) + Redis, Docker Compose, Alembic, CI
- **Phase 2** 인증·호출: JWT(access/refresh), bcrypt, 전화번호 Fernet 암호화, 호출 CRUD
- **Phase 3** 매칭 엔진 v1: 30초 배치, 하버사인 클러스터링, 우회 지수, Total Utility 최대화, 수락/거절/완료 상태 기계
- **Phase 4** 웹 프론트: Next.js — 로그인 → 호출 → 매칭 대기(폴링) → 수락/거절 → 완료
- **Phase 5** 실시간·신뢰: WebSocket 위치 공유(안심 경로), Redis 위치 캐시, 매칭 알림, 상호 평점
- **Phase 6** 안정화: Sentry(옵션), Faker 데모 시드, 커버리지 92%, CI에 커버리지 게이트(80%)

## 범위 제외 (PRD Out of Scope)

- 실결제(PG) — 정산 기록/시뮬레이션까지만
- 실지도 API — SVG 미니맵 (Kakao Maps 키 발급 후 교체 지점: `frontend/app/matches/[id]/page.js`의 `MiniMap`)
- 네이티브 앱, 기사용 배차 연동

## 데모 실행

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.demo_seed   # demo1~12@jnu.ac.kr / demo1234!
cd frontend && npm install && npm run dev              # http://localhost:3000
```
