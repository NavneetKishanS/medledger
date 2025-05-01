# backend/routes/sse.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import asyncio, json
from auth import get_current_user
from alert_buffer import get_alerts

router = APIRouter(prefix="/sse", tags=["alerts"])

async def stream(username: str):
    last = 0
    while True:
        alerts = get_alerts(username)
        if len(alerts) > last:
            for rec in alerts[:last*-1 or None]:
                yield f"data: {json.dumps(rec)}\n\n"
            last = len(alerts)
        await asyncio.sleep(1)

@router.get("/alerts")
async def sse_alerts(token: str):
    """
    Simple token query-param auth so EventSource can work.
    """
    try:
        payload = decode_token(token)          # returns {"sub": "patient1", ...}
        username = payload["sub"]
    except Exception:
        raise HTTPException(401, "bad token")

    return StreamingResponse(stream(username), media_type="text/event-stream")