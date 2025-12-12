"""
MongoDB connection & CRUD helpers for SCMXPertLite (Mongo-only mode).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import MongoClient

from config import MONGODB_DB, MONGODB_URL

logger = logging.getLogger(__name__)

SHIPMENTS_COLLECTION = "shipments"
DEVICE_EVENTS_COLLECTION = "device_events"
USERS_COLLECTION = "users"

mongo_client: Optional[MongoClient] = None
mongo_db = None


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _stringify_id(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not document:
        return None
    doc = document.copy()
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


def _ensure_db():
    if mongo_db is None:
        connect_to_mongo()
    return mongo_db


# -------------------------------------------------------------------
# Connection management
# -------------------------------------------------------------------
def connect_to_mongo():
    """Connect to MongoDB using the URI supplied in .env."""
    global mongo_client, mongo_db

    mongo_uri = MONGODB_URL
    if not mongo_uri:
        raise RuntimeError(
            "MONGODB_URL is not configured. Set it in your .env or environment."
        )

    retries = int(os.getenv("MONGO_CONNECT_RETRIES", "5"))
    delay = float(os.getenv("MONGO_CONNECT_DELAY", "2"))

    for attempt in range(1, retries + 1):
        try:
            print(f"[MongoDB] Connecting (attempt {attempt}/{retries})")
            mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
            mongo_client.admin.command("ping")
            mongo_db = mongo_client[MONGODB_DB]

            # Ensure indexes
            mongo_db[USERS_COLLECTION].create_index("email", unique=True)
            mongo_db[SHIPMENTS_COLLECTION].create_index(
                [("owner_id", 1), ("shipment_number", 1)], unique=True
            )
            mongo_db[DEVICE_EVENTS_COLLECTION].create_index("device_id")
            mongo_db[DEVICE_EVENTS_COLLECTION].create_index("owner_id")
            mongo_db[DEVICE_EVENTS_COLLECTION].create_index("timestamp")

            print("[MongoDB] ✅ Connected")
            logger.info("[MongoDB] Connected")
            return mongo_db
        except Exception as exc:
            logger.warning("[MongoDB] Connection failed: %s", exc)
            if attempt == retries:
                print("[MongoDB] ❌ All connection attempts failed")
                mongo_client = None
                mongo_db = None
                return None
            time.sleep(delay)
            delay *= 2


def disconnect_from_mongo():
    global mongo_client
    try:
        if mongo_client:
            mongo_client.close()
            mongo_client = None
            print("[MongoDB] Disconnected")
            logger.info("[MongoDB] Disconnected")
    except Exception as exc:
        logger.error("[MongoDB] Disconnect error: %s", exc)


# -------------------------------------------------------------------
# User helpers
# -------------------------------------------------------------------
def create_user_document(full_name: str, email: str, hashed_password: str, role: str):
    db = _ensure_db()
    if db is None:
        return None

    email_normalized = email.strip().lower()
    payload = {
        "full_name": full_name,
        "email": email_normalized,
        "hashed_password": hashed_password,
        "role": role,
        "created_at": datetime.utcnow(),
    }
    result = db[USERS_COLLECTION].insert_one(payload)
    inserted = db[USERS_COLLECTION].find_one({"_id": result.inserted_id})
    return _stringify_id(inserted)


def get_user_by_email(email: str):
    db = _ensure_db()
    if db is None:
        return None
    doc = db[USERS_COLLECTION].find_one({"email": email.strip().lower()})
    return _stringify_id(doc)


def get_user_by_id(user_id: str):
    db = _ensure_db()
    if db is None or not user_id:
        return None
    try:
        doc = db[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    return _stringify_id(doc)


def ensure_demo_user(full_name: str, email: str, hashed_password: str):
    if get_user_by_email(email):
        return
    create_user_document(full_name, email, hashed_password, role="shipment_manager")
    print("[MongoDB] ✅ Demo user seeded")


# -------------------------------------------------------------------
# Shipment helpers
# -------------------------------------------------------------------
def save_shipment_to_mongo(data: dict):
    db = _ensure_db()
    if db is None:
        return None

    payload = data.copy()
    payload.setdefault("created_at", datetime.utcnow())
    payload.setdefault("status", "created")
    payload["last_updated"] = datetime.utcnow()

    result = db[SHIPMENTS_COLLECTION].insert_one(payload)
    inserted = db[SHIPMENTS_COLLECTION].find_one({"_id": result.inserted_id})
    return _stringify_id(inserted)


def get_shipment_by_number(shipment_number: str, owner_id: Optional[str] = None):
    db = _ensure_db()
    if db is None:
        return None

    query = {"shipment_number": shipment_number}
    if owner_id:
        query["owner_id"] = owner_id
    doc = db[SHIPMENTS_COLLECTION].find_one(query)
    return _stringify_id(doc)


def get_shipments_from_mongo(owner_id: Optional[str] = None, limit: int = 100):
    db = _ensure_db()
    if db is None:
        return []

    query = {"owner_id": owner_id} if owner_id else {}

    items = (
        db[SHIPMENTS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    return [_stringify_id(item) for item in items]


def update_shipment_in_mongo(shipment_id: str, updates: dict):
    db = _ensure_db()
    if db is None:
        return False
    try:
        updates = updates.copy()
        updates["last_updated"] = datetime.utcnow()
        result = db[SHIPMENTS_COLLECTION].update_one(
            {"_id": ObjectId(shipment_id)}, {"$set": updates}
        )
        return result.modified_count > 0
    except Exception as exc:
        logger.error("[MongoDB] Update shipment error: %s", exc)
        return False


# -------------------------------------------------------------------
# Device event helpers
# -------------------------------------------------------------------
def save_device_event_to_mongo(data: dict):
    db = _ensure_db()
    if db is None:
        return None

    payload = data.copy()
    payload.setdefault("timestamp", datetime.utcnow())
    payload["created_at"] = datetime.utcnow()

    result = db[DEVICE_EVENTS_COLLECTION].insert_one(payload)
    return str(result.inserted_id)


def get_device_events_from_mongo(
    *,
    device_id: Optional[str] = None,
    shipment_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    db = _ensure_db()
    if db is None:
        return []

    query: Dict[str, Any] = {}
    if owner_id:
        query["owner_id"] = owner_id
    if device_id:
        query["device_id"] = device_id
    if shipment_id:
        query["shipment_id"] = shipment_id

    items = (
        db[DEVICE_EVENTS_COLLECTION]
        .find(query)
        .sort("timestamp", -1)
        .limit(limit)
    )
    return [_stringify_id(item) for item in items]


def get_mongo_db():
    return mongo_db
