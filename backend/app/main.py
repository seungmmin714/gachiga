import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.matches import router as matches_router
from app.api.rides import router as rides_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.match_runner import run_batch_matching

logger = logging.getLogger(__name__)


def _run_matching_once() -> list[dict]:
    with SessionLocal() as db:
        return run_batch_matching(db)


async def matching_loop():
    while True:
        await asyncio.sleep(settings.MATCH_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(_run_matching_once)
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


app = FastAPI(title="GACHIGA API", version="0.3.0", lifespan=lifespan)

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
