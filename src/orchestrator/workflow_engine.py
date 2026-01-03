import json
import time
from kafka import KafkaConsumer, KafkaProducer

class WorkflowEngine:
    def __init__(self):
        # 1. Producer to send tasks to agents
        self.producer = KafkaProducer(
            bootstrap_servers=['127.0.0.1:9092'],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # 2. Consumer to listen for COMPLETED tasks
        self.consumer = KafkaConsumer(
            'completed_tasks',
            bootstrap_servers=['127.0.0.1:9092'],
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # Define the Workflow State (The Memory)
        self.current_step = 0
        self.workflow_data = {} 

    def start_workflow(self, topic):
        """
        Defines the Workflow: Research -> Tweet
        """
        print(f"🚀 Starting Workflow for topic: {topic}")
        self.workflow_data['topic'] = topic
        
        # --- STEP 1: RESEARCH ---
        task_1 = {
            "id": "step_1",
            "description": f"Give me a short definition of {topic}.",
            "workflow_id": "flow_001"
        }
        self.send_task(task_1)
        self.wait_for_completion("step_1")

    def send_task(self, task):
        print(f"\n[Orchestrator] ➡️  Assigning Step: {task['description']}")
        self.producer.send('pending_tasks', value=task)
        self.producer.flush()

    def wait_for_completion(self, expected_task_id):
        """
        The Orchestrator pauses here until the Agent reports back.
        """
        print(f"[Orchestrator] ⏳ Waiting for Agent to finish {expected_task_id}...")
        
        for message in self.consumer:
            result_data = message.value
            
            if result_data['task_id'] == expected_task_id:
                print(f"[Orchestrator] ✅ Received Result from {result_data['agent']}")
                
                # Save the result to state
                self.workflow_data[expected_task_id] = result_data['result']
                
                # TRIGGER NEXT STEP LOGIC
                self.process_next_step(expected_task_id)
                return # Stop listening and move on
            
    def process_next_step(self, finished_step_id):
        """
        Decides what to do next based on the finished step.
        """
        if finished_step_id == "step_1":
            # Step 1 is done. Now do Step 2 (Summarize).
            prev_result = self.workflow_data['step_1']
            
            # --- STEP 2: TWEET ---
            task_2 = {
                "id": "step_2",
                "description": f"Write a funny tweet based on this text: '{prev_result}'",
                "workflow_id": "flow_001"
            }
            self.send_task(task_2)
            self.wait_for_completion("step_2")
            
        elif finished_step_id == "step_2":
            print("\n🎉 WORKFLOW COMPLETE! 🎉")
            print(f"Final Output: {self.workflow_data['step_2']}")
            exit()

if __name__ == "__main__":
    engine = WorkflowEngine()
    # We trigger the chain with a topic
    engine.start_workflow("Artificial Intelligence")