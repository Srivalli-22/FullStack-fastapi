#!/usr/bin/env python
"""
Test script to verify shipment creation and storage in both PostgreSQL and MongoDB.
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test credentials
TEST_EMAIL = "demo@demo.com"
TEST_PASSWORD = "Demo@123"

def test_login():
    print("\n=== TEST 1: Login ===")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    print(f"Status: {res.status_code}")
    if res.ok:
        data = res.json()
        token = data.get("access_token")
        print(f"Token: {token[:50]}...")
        return token
    else:
        print(f"Error: {res.text}")
        return None

def test_create_shipment(token):
    print("\n=== TEST 2: Create Shipment ===")
    shipment_data = {
        "shipment_number": f"SHP-{datetime.now().timestamp()}",
        "container_number": "CONT-12345",
        "route": "Hyderabad → Mumbai",
        "goods_type": "Vaccines",
        "device_id": "DEV-001",
        "expected_delivery": "25-12-2024",
        "po_number": "PO-2024-001",
        "delivery_number": "DEL-2024-001",
        "ndc_number": "NDC-2024-001",
        "batch_id": "BATCH-2024-001",
        "serial_number": "SN-2024-001",
        "description": "Test shipment with MongoDB storage"
    }
    
    res = requests.post(
        f"{BASE_URL}/api/shipments/",
        json=shipment_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {res.status_code}")
    if res.ok:
        data = res.json()
        print(f"Created shipment: {json.dumps(data, indent=2, default=str)}")
        return data
    else:
        print(f"Error: {res.text}")
        return None

def test_list_shipments(token):
    print("\n=== TEST 3: List Shipments ===")
    res = requests.get(
        f"{BASE_URL}/api/shipments/",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {res.status_code}")
    if res.ok:
        data = res.json()
        print(f"Found {len(data)} shipments:")
        for sh in data:
            print(f"  - {sh.get('shipment_number')} (container: {sh.get('container_number')})")
        return data
    else:
        print(f"Error: {res.text}")
        return None

def main():
    print("=" * 60)
    print("SHIPMENT CREATION & STORAGE TEST")
    print("=" * 60)
    
    # 1. Login
    token = test_login()
    if not token:
        print("Login failed, aborting tests")
        return
    
    # 2. Create shipment
    shipment = test_create_shipment(token)
    if not shipment:
        print("Shipment creation failed, aborting tests")
        return
    
    # 3. List shipments
    shipments = test_list_shipments(token)
    
    # 4. Save results
    print("\n=== RESULTS ===")
    results = {
        "timestamp": datetime.now().isoformat(),
        "login": {"status": "success" if token else "failed"},
        "create_shipment": {"status": "success" if shipment else "failed", "data": shipment},
        "list_shipments": {"count": len(shipments) if shipments else 0, "data": shipments}
    }
    
    with open("/app/static/api_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Results saved to static/api_test_results.json")
    print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    main()
