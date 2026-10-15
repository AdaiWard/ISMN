from __future__ import annotations

import asyncio

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import SessionLocal
from app.services.events import event_hub


router = APIRouter(tags=["События WebSocket"])


@router.websocket("/ws/events")
async def events_socket(websocket: WebSocket) -> None:
    authorization = websocket.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    try:
        payload = decode_access_token(token or "")
        with SessionLocal() as db:
            user = db.get(User, int(payload["sub"]))
            if not user or not user.is_active:
                raise ValueError("inactive")
    except (jwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=4401, reason="Требуется авторизация")
        return
    await websocket.accept()
    try:
        async for event in event_hub.subscribe():
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:
        return

