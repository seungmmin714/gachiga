import asyncio
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.matches import router as matches_router
from app.api.reviews import router as reviews_router
from app.api.rides import router as rides_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.match_runner import run_batch_matching
from app.ws.manager import manager
from app.ws.routes import router as ws_router

logger = logging.getLogger(__name__)

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)


def _run_matching_once() -> list[dict]:
    with SessionLocal() as db:
        return run_batch_matching(db)


async def matching_loop():
    while True:
        await asyncio.sleep(settings.MATCH_INTERVAL_SECONDS)
        try:
            summaries = await asyncio.to_thread(_run_matching_once)
            for summary in summaries:
                for user_id in summary["user_ids"]:
                    await manager.notify_user(
                        user_id, {"type": "match_proposed", "match_id": summary["match_id"]}
                    )
        except Exception:
            logger.exception("배치 매칭 실패")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.MATCHING_LOOP_ENABLED:
        task = asyncio.create_task(matching_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title="GACHIGA API", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(rides_router)
app.include_router(matches_router)
app.include_router(reviews_router)
app.include_router(ws_router)
