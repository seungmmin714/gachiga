from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models import Match, MatchMember
from app.services.locations import save_location
from app.ws.manager import manager

router = APIRouter()


def _authorize_match(token: str | None, match_id: int) -> int | None:
    """토큰 검증 + 매칭 멤버 확인. 통과 시 user_id 반환."""
    if not token:
        return None
    user_id = decode_token(token, "access")
    if user_id is None:
        return None
    with SessionLocal() as db:
        match = db.get(Match, match_id)
        if match is None:
            return None
        member = db.scalar(
            select(MatchMember).where(
                MatchMember.match_id == match_id, MatchMember.user_id == user_id
            )
        )
    return user_id if member else None


@router.websocket("/ws/matches/{match_id}")
async def match_channel(ws: WebSocket, match_id: int, token: str | None = None):
    user_id = _authorize_match(token, match_id)
    if user_id is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_match(match_id, ws)
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "location":
                try:
                    lat, lng = float(msg["lat"]), float(msg["lng"])
                except (KeyError, TypeError, ValueError):
                    continue
                payload = save_location(match_id, user_id, lat, lng)
                await manager.broadcast_match(match_id, payload)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_match(match_id, ws)


@router.websocket("/ws/rides")
async def user_channel(ws: WebSocket, token: str | None = None):
    """내 호출의 매칭 제안 알림 채널."""
    user_id = decode_token(token, "access") if token else None
    if user_id is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_user(user_id, ws)
    try:
        while True:
            await ws.receive_text()  # keepalive
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_user(user_id, ws)
