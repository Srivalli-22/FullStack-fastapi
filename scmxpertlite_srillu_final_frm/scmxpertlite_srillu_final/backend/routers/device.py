from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import schemas

from utils import get_current_user
from mongo_db import save_device_event_to_mongo, get_device_events_from_mongo
from kafkamod.producer import publish_device_event, generate_device_data

import logging
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/device', tags=['device'])

# Active SSE streams
active_streams = {}


# ============================================================
# 1. PUBLISH DEVICE EVENT
# ============================================================
@router.post('/publish')
def publish_message(event: schemas.DeviceEvent, user=Depends(get_current_user)):
    """Publish a device event to Kafka & save to MongoDB."""
    try:
        print(f"[device] Publishing event for device: {event.device_id}")

        payload = event.dict()
        payload["owner_id"] = user["id"]
        payload["owner_email"] = user["email"]
        payload["created_at"] = datetime.utcnow()

        mongo_id = save_device_event_to_mongo(payload)

        kafka_payload = {**event.dict(), "owner_id": user["id"], "owner_email": user["email"]}
        event_id = publish_device_event(kafka_payload, event.shipment_id)

        return {
            "status": "success",
            "event_id": event_id,
            "mongo_id": mongo_id
        }

    except Exception as e:
        logger.error(f"[device] Error publishing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2. GET RECENT EVENTS
# ============================================================
@router.get('/recent')
def get_recent_events(
    device_id: str = Query(None),
    shipment_id: str = Query(None),
    limit: int = Query(50),
    user=Depends(get_current_user)
):
    try:
        events = get_device_events_from_mongo(
            device_id=device_id,
            shipment_id=shipment_id,
            owner_id=user["id"],
            limit=limit
        )

        return events
    except Exception as e:
        logger.error(f"[device] Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3. STREAM DEVICE DATA (SSE)
# ============================================================
@router.get('/stream/{device_id}')
async def stream_device_data(device_id: str, user=Depends(get_current_user)):
    """Real-time streaming using SSE."""

    async def event_generator():
        stream_key = f"{device_id}:{user['id']}"
        active_streams[stream_key] = True

        try:
            while active_streams.get(stream_key):
                data = generate_device_data(device_id)

                save_device_event_to_mongo({
                    **data,
                    "owner_id": user["id"],
                    "owner_email": user["email"],
                    "created_at": datetime.utcnow()
                })

                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(2)

        finally:
            active_streams.pop(stream_key, None)
            print(f"[device] Stream closed for {device_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ============================================================
# 4. GENERATE SINGLE EVENT
# ============================================================
@router.get('/generate/{device_id}')
def generate_single_event(
    device_id: str,
    shipment_id: str = Query(None),
    user=Depends(get_current_user)
):
    try:
        data = generate_device_data(device_id)

        mongo_id = save_device_event_to_mongo({
            **data,
            "shipment_id": shipment_id,
            "owner_id": user["id"],
            "owner_email": user["email"],
            "created_at": datetime.utcnow()
        })

        kafka_payload = {**data, "owner_id": user["id"], "owner_email": user["email"]}
        event_id = publish_device_event(kafka_payload, shipment_id)

        return {
            "status": "success",
            "event_id": event_id,
            "mongo_id": mongo_id,
            "data": data
        }

    except Exception as e:
        logger.error(f"[device] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
