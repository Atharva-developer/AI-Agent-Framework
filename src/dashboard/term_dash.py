import os
import time
import json
import threading
from kafka import KafkaConsumer

# -- GLOBAL MEMORY --
pending_tasks = []
completed_tasks = []

def listen_to_kafka():
    """Background listener that quietly updates our lists"""
    consumer = KafkaConsumer(
        'pending_tasks', 'completed_tasks',
        bootstrap_servers=['localhost:9092'],
        api_version=(0, 10, 1), # The critical fix
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    for message in consumer:
        data = message.value
        if message.topic == 'pending_tasks':
            pending_tasks.append(data)
        elif message.topic == 'completed_tasks':
            completed_tasks.append(data)

# Start the listener in a separate background thread
t = threading.Thread(target=listen_to_kafka, daemon=True)
t.start()

# -- THE DASHBOARD LOOP --
def print_dashboard():
    while True:
        # Clear the terminal screen (works on Mac)
        os.system('clear')
        
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║   🤖  INTEL AI AGENT FRAMEWORK - MISSION CONTROL (LIVE)      ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║   System Status:  🟢 ONLINE                                  ║")
        print(f"║   Active Agents:  1 (LiteWorker)                             ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print("\n")

        # SECTION 1: PENDING TASKS
        print("📨  PENDING TASK QUEUE")
        print("────────────────────────────────────────────────────────────────")
        if not pending_tasks:
            print("   (No tasks waiting...)")
        else:
            # Show last 5 tasks
            for task in reversed(pending_tasks[-5:]):
                print(f"   [ID: {task.get('id')}] -> {task.get('description')}")
        
        print("\n")

        # SECTION 2: COMPLETED LOG
        print("✅  COMPLETED RESULTS")
        print("────────────────────────────────────────────────────────────────")
        if not completed_tasks:
            print("   (No results yet...)")
        else:
            # Show last 5 results
            for res in reversed(completed_tasks[-5:]):
                print(f"   [Task: {res.get('task_id')}] RESULT: {res.get('result')}")
                print(f"   └── Processed by: {res.get('agent')}")
                print("   ---")

        print("\n")
        print("Press Ctrl+C to Exit...")
        time.sleep(2) # Refresh every 2 seconds

if __name__ == "__main__":
    print("Starting Dashboard...")
    print_dashboard()