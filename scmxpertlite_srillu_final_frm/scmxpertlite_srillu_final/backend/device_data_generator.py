#!/usr/bin/env python
"""
Device Data Generator - Mimics server 2.py pattern
Generates realistic device data and sends to Kafka
Pattern: generator → Kafka → consumer → PostgreSQL/MongoDB
"""

import json
import random
import time
from datetime import datetime
from kafkamod.producer import produce_topic
from config import DEVICE_TOPIC

# Routes similar to server 2.py
ROUTES = [
    ('Hyderabad, India', 'Mumbai, India'),
    ('Chennai, India', 'Bangalore, India'),
    ('Pune, India', 'Delhi, India'),
    ('Kolkata, India', 'Bangalore, India'),
    ('New York, USA', 'Los Angeles, USA'),
    ('London, UK', 'Manchester, UK'),
    ('Sydney, Australia', 'Melbourne, Australia'),
    ('Dubai, UAE', 'Abu Dhabi, UAE')
]

DEVICE_IDS = [f'DEV-{i:03d}' for i in range(1, 21)]  # DEV-001 to DEV-020

def generate_device_event():
    """Generate a single device data event"""
    from_route, to_route = random.choice(ROUTES)
    
    event = {
        "device_id": random.choice(DEVICE_IDS),
        "battery": round(random.uniform(20, 100), 2),  # 20-100%
        "temperature": f"{round(random.uniform(5, 50), 1)}°C",  # 5-50°C
        "route_from": from_route,
        "route_to": to_route,
        "timestamp": datetime.utcnow().isoformat(),
        "status": random.choice(["active", "idle", "charging"]),
        "location": {
            "latitude": round(random.uniform(-90, 90), 4),
            "longitude": round(round.uniform(-180, 180), 4)
        }
    }
    
    return event

def generate_batch(count=5):
    """Generate multiple device events"""
    events = []
    for _ in range(count):
        events.append(generate_device_event())
    return events

def stream_device_data(interval=10, batch_size=1):
    """
    Stream device data continuously
    interval: seconds between batches
    batch_size: number of events per batch
    """
    print("=" * 70)
    print("DEVICE DATA GENERATOR (Similar to server 2.py)")
    print("=" * 70)
    print(f"[generator] Starting to stream device data...")
    print(f"[generator] Interval: {interval}s, Batch Size: {batch_size}")
    print(f"[generator] Topic: {DEVICE_TOPIC}")
    print("=" * 70)
    print()
    
    event_count = 0
    
    while True:
        try:
            # Generate batch
            batch = generate_batch(batch_size)
            
            for event in batch:
                # Publish to Kafka
                success = produce_topic(DEVICE_TOPIC, event)
                
                if success:
                    event_count += 1
                    print(f"[generator #{event_count}] {event['device_id']} | "
                          f"Battery: {event['battery']}% | "
                          f"Temp: {event['temperature']} | "
                          f"Route: {event['route_from']} → {event['route_to']}")
                else:
                    print(f"[generator] ⚠️ Failed to publish event")
            
            print(f"[generator] Sleeping for {interval}s...")
            print()
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print()
            print("=" * 70)
            print(f"[generator] Stopping... (published {event_count} total events)")
            print("=" * 70)
            break
        except Exception as e:
            print(f"[generator] ❌ Error: {e}")
            print(f"[generator] Retrying in 5s...")
            time.sleep(5)

def simulate_multi_device_stream(num_devices=5, events_per_device=3):
    """
    Simulate multiple devices sending data simultaneously
    """
    print("=" * 70)
    print("MULTI-DEVICE STREAM SIMULATOR")
    print("=" * 70)
    print(f"[simulator] {num_devices} devices, {events_per_device} events each")
    print("=" * 70)
    print()
    
    try:
        for batch_num in range(1, 100):  # 100 batches
            print(f"\n[batch #{batch_num}]")
            for device_num in range(num_devices):
                event = generate_device_event()
                success = produce_topic(DEVICE_TOPIC, event)
                if success:
                    print(f"  ├─ {event['device_id']}: {event['battery']}% battery, "
                          f"{event['temperature']}")
                else:
                    print(f"  ├─ ⚠️ Failed to send {event['device_id']}")
            
            print(f"  └─ Waiting 15s before next batch...")
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n[simulator] Stopped by user")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "multi":
            simulate_multi_device_stream()
        else:
            interval = int(sys.argv[1]) if sys.argv[1].isdigit() else 10
            stream_device_data(interval=interval)
    else:
        stream_device_data(interval=10, batch_size=1)
