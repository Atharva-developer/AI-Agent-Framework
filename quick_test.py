#!/usr/bin/env python3
"""
Quick test of single task submission and result retrieval.
"""

import requests
import json
import time

API_URL = "http://127.0.0.1:8000"
API_KEY = "sk-default-admin-key"

def test_api():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing API with single task...")
    print()
    
    # Test 1: Health check
    print("1️⃣ Health check:")
    response = requests.get(f"{API_URL}/health", timeout=5)
    print(f"   Status: {response.status_code}")
    health = response.json()
    print(f"   System: {json.dumps(health, indent=2)}")
    print()
    
    # Test 2: Submit a calculation task
    print("2️⃣ Submit task (calculate 10 + 5):")
    response = requests.post(
        f"{API_URL}/tasks",
        json={"description": "calculate 10 + 5"},
        headers=headers,
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    task = response.json()
    task_id = task['id']
    print(f"   Task ID: {task_id}")
    print(f"   Status: {task['status']}")
    print()
    
    # Test 3: Wait and check result
    print("3️⃣ Waiting for result (30 seconds max)...")
    for i in range(15):
        time.sleep(2)
        
        response = requests.get(
            f"{API_URL}/tasks/{task_id}",
            headers=headers,
            timeout=5
        )
        task = response.json()
        status = task['status']
        
        if status == 'completed':
            print(f"   ✅ Complete!")
            print(f"   Result: {task['result']}")
            break
        else:
            print(f"   ⏳ Status: {status}... ({i*2+2}s)")
    
    print()
    print("✨ Test complete!")

if __name__ == "__main__":
    test_api()
