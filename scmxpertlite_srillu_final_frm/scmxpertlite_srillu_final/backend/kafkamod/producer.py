"""Kafka Producer for SCMXPertLite - Real-time Data Streaming

This module provides a small, robust Kafka producer and helper methods
for publishing shipment and device events. It also includes a simple
device-data publisher loop (for local/testing use) that saves events to
MongoDB as a backup.
"""
import os
from kafka import KafkaProducer
import json
import logging
from datetime import datetime
import uuid
import random
import time
from mongo_db import save_device_event_to_mongo

logger = logging.getLogger(__name__)

# Kafka Configuration
# Read bootstrap/server from env so container can use the docker service name
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
SHIPMENT_TOPIC = "shipments"
DEVICE_EVENTS_TOPIC = "device_events"

# Global Kafka producer
kafka_producer = None


def get_producer():
	"""Get or create Kafka producer"""
	global kafka_producer
	if kafka_producer is None:
		try:
			kafka_producer = KafkaProducer(
				bootstrap_servers=[KAFKA_BROKER],
				# Use json.dumps with default=str to ensure datetimes are serialized to ISO strings
				value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
				acks="all",
				retries=3,
				linger_ms=5,
			)
			logger.info("[Kafka] ✅ Producer initialized successfully")
		except Exception as e:
			logger.error(f"[Kafka] ❌ Producer initialization failed: {e}")
			kafka_producer = None
	return kafka_producer


def publish_shipment(shipment_data: dict):
	"""Publish shipment creation event to Kafka."""
	try:
		producer = get_producer()
		if producer is None:
			logger.warning("[Kafka] Producer not available, skipping publish")
			return None

		event = {
			"event_type": "shipment_created",
			"event_id": str(uuid.uuid4()),
			"timestamp": datetime.utcnow().isoformat(),
			"data": shipment_data,
		}

		future = producer.send(SHIPMENT_TOPIC, value=event)
		future.get(timeout=10)

		logger.info(f"[Kafka] ✅ Shipment published: {event['event_id']}")
		return event["event_id"]
	except Exception as e:
		logger.error(f"[Kafka] ❌ Failed to publish shipment: {e}")
		return None


def publish_device_event(device_data: dict, shipment_id: str = None):
	"""Publish a single device event to Kafka."""
	try:
		producer = get_producer()
		if producer is None:
			logger.warning("[Kafka] Producer not available, skipping device publish")
			return None

		event = {
			"event_type": "device_event",
			"event_id": str(uuid.uuid4()),
			"timestamp": datetime.utcnow().isoformat(),
			"shipment_id": shipment_id,
			"data": device_data,
		}

		future = producer.send(DEVICE_EVENTS_TOPIC, value=event)
		future.get(timeout=10)

		logger.debug(f"[Kafka] Device event published: {event['event_id']}")
		return event["event_id"]
	except Exception as e:
		logger.error(f"[Kafka] ❌ Failed to publish device event: {e}")
		return None


def publish_device_stream(device_id: str, shipment_id: str = None):
	"""Generate one device data point and publish it to Kafka (helper used by device router)."""
	try:
		device_data = generate_device_data(device_id)
		return publish_device_event(device_data, shipment_id)
	except Exception as e:
		logger.error(f"[Kafka] ❌ Failed to publish device stream: {e}")
		return None


def test_connection() -> bool:
	"""Quick test that the Kafka producer can send a small message."""
	try:
		producer = get_producer()
		if producer is None:
			logger.warning("[Kafka] Producer not available for test")
			return False
		test_event = {"event_type": "test", "timestamp": datetime.utcnow().isoformat()}
		future = producer.send(SHIPMENT_TOPIC, value=test_event)
		future.get(timeout=5)
		logger.info("[Kafka] ✅ Connection test successful")
		return True
	except Exception as e:
		logger.error(f"[Kafka] ❌ Connection test failed: {e}")
		return False


def generate_device_data(device_id: str = None):
	"""Generate realistic device sensor data for testing or streaming."""
	routes = [
		("Hyderabad, India", "Mumbai, India"),
		("Chennai, India", "Bangalore, India"),
		("Pune, India", "Delhi, India"),
		("Kolkata, India", "Bangalore, India"),
		("New York, USA", "Los Angeles, USA"),
		("London, UK", "Berlin, Germany"),
	]

	route_from, route_to = random.choice(routes)

	return {
		"device_id": device_id or f"DEV-{random.randint(1000,9999)}",
		"timestamp": datetime.utcnow().isoformat(),
		"battery": round(random.uniform(20, 100), 2),
		"temperature": round(random.uniform(5, 35), 2),
		"humidity": round(random.uniform(30, 90), 2),
		"latitude": round(random.uniform(12.8, 13.0), 6),
		"longitude": round(random.uniform(79.7, 79.9), 6),
		"altitude": round(random.uniform(0, 500), 2),
		"speed": round(random.uniform(0, 80), 2),
		"accuracy": round(random.uniform(5, 20), 2),
		"route_from": route_from,
		"route_to": route_to,
		"status": random.choice(["in_transit", "delivered", "in_warehouse"]),
	}


def publish_device_data(loop_delay: int = 10, device_id: str = None, shipment_id: str = None):
	"""Continuously publish device data to Kafka and save to MongoDB as backup.

	This is a convenience helper for local testing and follows the "server 2.py"
	pattern: generate → publish → save.
	"""
	logger.info("[producer] Starting device data publisher loop")
	try:
		while True:
			device_data = generate_device_data(device_id)

			evt_id = publish_device_event(device_data, shipment_id)
			if evt_id:
				# Save to MongoDB as backup (best-effort)
				try:
					mongo_payload = {**device_data, "created_at": datetime.utcnow(), "source": "producer"}
					save_device_event_to_mongo(mongo_payload)
				except Exception as e:
					logger.warning(f"[producer] Failed saving to MongoDB: {e}")

				logger.info(f"[producer] Published device {device_data['device_id']} (evt={evt_id})")

			time.sleep(loop_delay)
	except KeyboardInterrupt:
		logger.info("[producer] Stopping publisher loop (KeyboardInterrupt)")
	except Exception as e:
		logger.error(f"[producer] Unhandled error in publisher loop: {e}")


def close_producer():
	"""Close Kafka producer connection"""
	global kafka_producer
	try:
		if kafka_producer:
			kafka_producer.close()
			kafka_producer = None
			logger.info("[Kafka] ✅ Producer closed successfully")
	except Exception as e:
		logger.error(f"[Kafka] ❌ Error closing producer: {e}")


if __name__ == "__main__":
	# Allow quick manual run: python -m backend.kafkamod.producer
	try:
		publish_device_data()
	finally:
		close_producer()
