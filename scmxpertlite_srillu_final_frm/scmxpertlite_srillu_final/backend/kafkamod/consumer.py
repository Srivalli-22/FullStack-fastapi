"""
Kafka Consumer for SCMXPertLite - reads Kafka topics and writes to MongoDB.
Fully cleaned, safe, and fixed version.
"""

import json
import time
import logging
import os
import threading
from datetime import datetime

from kafka import KafkaConsumer

from mongo_db import (
    connect_to_mongo,
    save_device_event_to_mongo,
    save_shipment_to_mongo,
    get_shipment_by_number,
    update_shipment_in_mongo,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ------------------- CONFIG -------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
SHIPMENT_TOPIC = "shipments"
DEVICE_EVENTS_TOPIC = "device_events"


# ------------------- KAFKA CONSUMER BUILDER -------------------
def build_consumer(topic: str, group_id: str):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=group_id,
            session_timeout_ms=30000,
        )
        logger.info("[Consumer] ✅ Ready for topic: %s", topic)
        return consumer
    except Exception as exc:
        logger.error("[Consumer] ❌ Failed to create consumer for %s: %s", topic, exc)
        return None


# ------------------- SHIPMENT HANDLER -------------------
def process_shipment_message(message_data: dict):
    try:
        shipment_data = message_data.get("data", {})
        if not shipment_data:
            logger.warning("[Consumer] ⚠️ Shipment event missing data")
            return None

        shipment_data.setdefault("source", "kafka_consumer")

        existing = get_shipment_by_number(
            shipment_data.get("shipment_number"),
            owner_id=shipment_data.get("owner_id"),
        )

        if existing:
            update_shipment_in_mongo(existing["id"], shipment_data)
            logger.info("[Consumer] 🔁 Shipment updated: %s", shipment_data.get("shipment_number"))
            return existing

        saved = save_shipment_to_mongo(shipment_data)
        if saved:
            logger.info("[Consumer] ✅ Shipment stored: %s", shipment_data.get("shipment_number"))
            return saved

        logger.warning("[Consumer] ⚠️ Failed to store shipment: %s", shipment_data.get("shipment_number"))
        return None

    except Exception as exc:
        logger.error("[Consumer] ❌ Shipment processing error: %s", exc)
        return None


# ------------------- DEVICE EVENT HANDLER -------------------
def process_device_message(message_data: dict):
    try:
        device_data = message_data.get("data", {})
        shipment_id = message_data.get("shipment_id")

        if not device_data:
            logger.warning("[Consumer] ⚠️ Device event missing data")
            return None

        payload = {
            **device_data,
            "shipment_id": shipment_id,
            "timestamp": datetime.utcnow(),
            "source": "kafka_consumer",
        }

        mongo_id = save_device_event_to_mongo(payload)
        if mongo_id:
            logger.info("[Consumer] ✅ Device event stored for: %s", device_data.get("device_id"))
        else:
            logger.warning("[Consumer] ⚠️ Failed to store device event")

        return mongo_id

    except Exception as exc:
        logger.error("[Consumer] ❌ Device event error: %s", exc)
        return None


# ------------------- CONSUMER LOOP -------------------
def consume(topic: str, group_id: str, handler):
    consumer = build_consumer(topic, group_id)
    if consumer is None:
        logger.error("[Kafka Consumer] ❌ Cannot start consumer for topic %s", topic)
        return

    logger.info("[Kafka Consumer] 🔄 Listening for events on topic: %s", topic)

    for message in consumer:
        try:
            handler(message.value)
        except Exception as exc:
            logger.error("[Consumer] ❌ Error in message handler: %s", exc)


# ------------------- MAIN -------------------
if __name__ == "__main__":
    print("[Kafka Consumer] Starting...")
    print(f"[Kafka Consumer] Using Kafka broker: {KAFKA_BROKER}")

    print("[Kafka Consumer] Connecting to MongoDB...")
    mongo_connection = connect_to_mongo()

    if mongo_connection is not None:
        print("[Kafka Consumer] ✅ MongoDB connected")
    else:
        print("[Kafka Consumer] ⚠️ MongoDB NOT connected (retry will happen later)")

    # Start shipments consumer in separate thread
    shipment_thread = threading.Thread(
        target=consume,
        args=(SHIPMENT_TOPIC, "shipment_consumer_group", process_shipment_message),
        daemon=True,
        name="shipment-consumer",
    )
    shipment_thread.start()

    # Main thread handles device events
    try:
        consume(DEVICE_EVENTS_TOPIC, "device_consumer_group", process_device_message)
    except KeyboardInterrupt:
        print("[Kafka Consumer] Shutdown requested...")
    except Exception as exc:
        logger.error("[Kafka Consumer] ❌ Fatal error: %s", exc)
        print("[Kafka Consumer] Restarting in 5 seconds...")
        time.sleep(5)
