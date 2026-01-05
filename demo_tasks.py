#!/usr/bin/env python3
"""
Multi-task submission demo script.
Submit various types of tasks to test the agent framework.
"""

import requests
import json
import time
from typing import List, Dict

API_URL = "http://127.0.0.1:8000"
API_KEY = "sk-default-admin-key"

# Sample tasks of different types
DEMO_TASKS = [
    {
        "name": "Calculate Simple Math",
        "description": "calculate 150 * 4"
    },
    {
        "name": "Calculate Complex Expression",
        "description": "calculate (100 + 50) / 2 - 25"
    },
    {
        "name": "Analyze Text",
        "description": "analyze text the quick brown fox jumps over the lazy dog. this is a second sentence. and a third."
    },
    {
        "name": "Convert to Uppercase",
        "description": "uppercase hello world"
    },
    {
        "name": "Convert to Lowercase",
        "description": "lowercase HELLO WORLD"
    },
    {
        "name": "Reverse String",
        "description": "reverse hello"
    },
    {
        "name": "Summarize Text",
        "description": "summarize Machine learning is a subset of artificial intelligence that focuses on the development of algorithms. These algorithms can learn from data without being explicitly programmed. Deep learning is a branch of machine learning."
    },
    {
        "name": "Word Count",
        "description": "count words the framework supports distributed task processing with kafka messaging and persistent storage."
    }
]


def submit_task(description: str) -> Dict:
    """Submit a single task to the API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {"description": description}
    
    try:
        response = requests.post(
            f"{API_URL}/tasks",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def get_task_status(task_id: str) -> Dict:
    """Get status of a task."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{API_URL}/tasks/{task_id}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def get_health() -> Dict:
    """Check system health."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Health check failed"}
    except Exception as e:
        return {"error": str(e)}


def main():
    """Main demo function."""
    print("\n" + "="*70)
    print("🚀 Multi-Task Demo - AI Agent Framework")
    print("="*70 + "\n")
    
    # Check health
    print("📡 Checking system health...")
    health = get_health()
    if "error" in health:
        print(f"❌ Health check failed: {health['error']}")
        return
    
    print(f"✅ System healthy")
    print(f"   - Agents online: {health.get('agents_online', 0)}")
    print(f"   - Tasks pending: {health.get('tasks_pending', 0)}")
    print()
    
    # Submit all tasks
    print("📤 Submitting tasks...\n")
    task_ids = []
    
    for idx, task in enumerate(DEMO_TASKS, 1):
        print(f"{idx}. {task['name']}")
        print(f"   Task: {task['description']}")
        
        result = submit_task(task['description'])
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            task_id = result.get('id')
            task_ids.append(task_id)
            print(f"   ✅ Submitted (ID: {task_id})")
        
        time.sleep(0.2)  # Small delay between submissions
    
    print(f"\n📊 Submitted {len(task_ids)} tasks. Waiting for results...\n")
    
    # Poll for results
    max_wait = 30  # seconds
    start_time = time.time()
    completed = 0
    
    while completed < len(task_ids) and (time.time() - start_time) < max_wait:
        time.sleep(2)
        completed = 0
        
        for task_id in task_ids:
            status = get_task_status(task_id)
            
            if "error" in status:
                continue
            
            if status.get('status') == 'completed':
                completed += 1
        
        elapsed = int(time.time() - start_time)
        print(f"⏳ {elapsed}s elapsed... {completed}/{len(task_ids)} tasks completed", end="\r")
    
    print()
    
    # Display results
    print("\n" + "="*70)
    print("📋 Results")
    print("="*70 + "\n")
    
    for task_id in task_ids:
        status = get_task_status(task_id)
        
        if "error" in status:
            print(f"Task {task_id}: ❌ Error")
            continue
        
        print(f"Task ID: {task_id}")
        print(f"Status: {status.get('status', 'unknown')}")
        print(f"Description: {status.get('description', 'N/A')}")
        print(f"Result: {status.get('result', 'No result yet')}")
        print("-" * 70)
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()
