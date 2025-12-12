from fastapi import APIRouter, Depends, HTTPException
import schemas
from utils import get_current_user
from mongo_db import (
    save_shipment_to_mongo,
    get_shipments_from_mongo,
    get_shipment_by_number,
)
from kafkamod.producer import publish_shipment
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.post("/", response_model=schemas.ShipmentOut, status_code=201)
def create_shipment(
    sh: schemas.ShipmentCreate,
    current_user: dict = Depends(get_current_user),
):
    logger.info(f"[shipment-create] User: {current_user['email']}  Data: {sh.dict()}")

    existing = get_shipment_by_number(sh.shipment_number, owner_id=current_user["id"])
    if existing:
        raise HTTPException(status_code=400, detail="Shipment number already exists")

    mongo_data = {
        **sh.dict(),
        "owner_id": current_user["id"],
        "owner_email": current_user["email"],
        "created_at": datetime.utcnow(),
        "status": "created",
    }
    saved = save_shipment_to_mongo(mongo_data)
    if not saved:
        raise HTTPException(status_code=500, detail="Unable to save shipment")

    publish_shipment(saved)
    return saved


@router.get("/", response_model=list[schemas.ShipmentOut])
def list_shipments(current_user: dict = Depends(get_current_user)):
    logger.info(f"[shipments-list] User: {current_user['email']} (id={current_user['id']})")
    items = get_shipments_from_mongo(owner_id=current_user["id"])
    logger.info(f"[shipments-list] Found {len(items)} shipments")
    return items
