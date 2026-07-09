"""WebSocket 연결 관리 — 매칭 채널(위치 공유)과 사용자 채널(매칭 알림)."""

from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.match_rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self.user_channels: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect_match(self, match_id: int, ws: WebSocket):
        await ws.accept()
        self.match_rooms[match_id].add(ws)

    def disconnect_match(self, match_id: int, ws: WebSocket):
        self.match_rooms[match_id].discard(ws)

    async def connect_user(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.user_channels[user_id].add(ws)

    def disconnect_user(self, user_id: int, ws: WebSocket):
        self.user_channels[user_id].discard(ws)

    async def broadcast_match(self, match_id: int, message: dict):
        for ws in list(self.match_rooms.get(match_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                self.match_rooms[match_id].discard(ws)

    async def notify_user(self, user_id: int, message: dict):
        for ws in list(self.user_channels.get(user_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                self.user_channels[user_id].discard(ws)


manager = ConnectionManager()
