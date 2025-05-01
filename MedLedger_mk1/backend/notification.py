from collections import defaultdict, deque
from typing import Dict, Deque, Any, Set
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

_VITAL_HISTORY: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=100))
_CONNECTIONS: Dict[str, Set[WebSocket]] = defaultdict(set)


def store_vital(patient_id: str, record: dict) -> None:
    _VITAL_HISTORY[patient_id].appendleft(record)


def list_vitals(patient_id: str) -> list[dict]:
    return list(_VITAL_HISTORY[patient_id])


def list_alerts(patient_id: str) -> list[dict]:
    return [v for v in _VITAL_HISTORY[patient_id] if v.get("anomaly")]


async def register_ws(patient_id: str, ws: WebSocket) -> None:
    await ws.accept()
    _CONNECTIONS[patient_id].add(ws)


def unregister_ws(patient_id: str, ws: WebSocket) -> None:
    _CONNECTIONS[patient_id].discard(ws)


async def broadcast_alert(patient_id: str, payload: dict) -> None:
    dead = set()
    for ws in _CONNECTIONS[patient_id]:
        try:
            await ws.send_json(payload)
        except (RuntimeError, WebSocketDisconnect):
            dead.add(ws)
    for ws in dead:
        unregister_ws(patient_id, ws)
