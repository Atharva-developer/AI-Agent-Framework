import json
from kafka import KafkaProducer

# 1. Setup the connection to the Docker Kafka
# We force api_version to skip the handshake check which often fails on Mac
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    api_version=(0, 10, 1),  # <--- THIS IS THE CRITICAL FIX
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

def send_task(task_description):
    """
    Sends a job to the 'pending_tasks' topic.
    """
    task_payload = {
        "id": "task_math_01",
        "description": task_description,
        "assigned_agent": "IntelWorker-1"
    }
    
    print(f"Manager: 📤 Sending task to Kafka: '{task_description}'")
    
    # Send to topic 'pending_tasks'
    producer.send('pending_tasks', value=task_payload)
    producer.flush() # Force send immediately

if __name__ == "__main__":
    print("Manager: Starting up...")
    
    # TEST: Send a calculation command to test the new Tool
    send_task("calculate 150 * 4")
    
    print("Manager: Task sent successfully.")