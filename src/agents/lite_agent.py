import json
import time
from kafka import KafkaConsumer, KafkaProducer

class LiteAgent:
    def __init__(self, name: str):
        self.name = name
        
        # Connect to Kafka (Standard Setup)
        print(f"[{self.name}] 🔌 Connecting to Kafka...")
        self.consumer = KafkaConsumer(
            'pending_tasks',
            bootstrap_servers=['localhost:9092'],
            api_version=(0, 10, 1),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='lite_group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            api_version=(0, 10, 1),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        print(f"[{self.name}] ✅ Ready (Lite Mode - No Heavy AI Model)")

    def start_listening(self):
        print(f"[{self.name}] 👂 Listening for tasks...")
        for message in self.consumer:
            task_data = message.value
            print(f"[{self.name}] 📨 Picked up task: {task_data['description']}")
            
            # Process the task (Tools only, no LLM)
            result = self.process_task(task_data['description'])
            
            self.send_result(task_data['id'], result)

    def process_task(self, task_input):
        # 1. TOOL USAGE: Calculator
        if "calculate" in task_input.lower():
            print(f"[{self.name}] 🛠️ Tool Triggered: Calculator")
            return self._use_calculator_tool(task_input)

        # 2. FALLBACK (Since we have no Brain in Lite Mode)
        return "I am a Lite Agent. I can only perform calculations right now."

    def _use_calculator_tool(self, query):
        try:
            math_expression = query.lower().replace("calculate", "").replace("please", "").strip()
            # Simple safety check
            allowed = set("0123456789+-*/(). ")
            if not set(math_expression).issubset(allowed):
                return "Error: unsafe characters."
            result = eval(math_expression)
            response = f"Result: {result}"
        except Exception as e:
            response = f"Error: {e}"
        print(f"[{self.name}] 🔢 Tool Output: {response}")
        return response

    def send_result(self, task_id, result):
        result_payload = {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "agent": self.name
        }
        self.producer.send('completed_tasks', value=result_payload)
        self.producer.flush()
        print(f"[{self.name}] 📤 Result sent back.\n")

if __name__ == "__main__":
    agent = LiteAgent(name="LiteWorker-1")
    agent.start_listening()