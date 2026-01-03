import json
import time
import torch
from kafka import KafkaConsumer, KafkaProducer

# Try to import Intel OpenVINO
try:
    from optimum.intel import OVModelForCausalLM
    from transformers import AutoTokenizer, pipeline
    INTEL_IMPORTS_OK = True
except ImportError:
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    INTEL_IMPORTS_OK = False

class Agent:
    def __init__(self, name: str, role: str, model_id: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        self.name = name
        self.role = role
        self.model_id = model_id
        
        # 1. Setup Kafka Consumer (API Version Fixed here)
        print(f"[{self.name}] 🔌 Connecting to Kafka...")
        self.consumer = KafkaConsumer(
            'pending_tasks',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='agent_group_1',
            api_version=(0, 10, 1),  # <--- FIX: Forces connection without handshake
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # 2. Setup Kafka Producer (API Version Fixed here)
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            api_version=(0, 10, 1),  # <--- FIX: Forces connection without handshake
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )

        # 3. LOAD THE BRAIN (Safe Mode)
        print(f"[{self.name}] ⏳ Loading AI Model ({model_id})...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        
        self.model = None
        
        # Attempt Intel Optimization
        if INTEL_IMPORTS_OK:
            try:
                print(f"[{self.name}] 🚀 Attempting Intel OpenVINO Optimization...")
                # We wrap this in a try-block because it often fails on Macs (Apple Silicon)
                self.model = OVModelForCausalLM.from_pretrained(model_id, export=True)
                print(f"[{self.name}] ✅ Intel Optimization Successful!")
            except Exception as e:
                print(f"[{self.name}] ⚠️ Intel Optimization Failed (Likely due to Mac M1/M2 chip).")
                print(f"[{self.name}] ℹ️ Error detail: {e}")
                print(f"[{self.name}] 🔄 Falling back to Standard PyTorch mode...")
                self.model = None # Reset to force fallback

        # Fallback if Intel failed or wasn't imported
        if self.model is None:
            self.model = AutoModelForCausalLM.from_pretrained(model_id)
            print(f"[{self.name}] 🐢 Loaded in Standard Mode (Non-Intel).")

        # Create the pipeline
        self.pipe = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer, max_new_tokens=100)
        print(f"[{self.name}] 🧠 Brain Loaded & Ready!")

    def start_listening(self):
        print(f"[{self.name}] 👂 Listening for tasks on Kafka...")
        for message in self.consumer:
            task_data = message.value
            print(f"[{self.name}] 📨 Picked up task: {task_data['description']}")
            result = self.process_task(task_data['description'])
            self.send_result(task_data['id'], result)

    def process_task(self, task_input):
        # 1. TOOL USAGE: Calculator
        if "calculate" in task_input.lower():
            print(f"[{self.name}] 🛠️ Tool Triggered: Calculator")
            return self._use_calculator_tool(task_input)

        # 2. STANDARD AI
        prompt = f"<|system|>\n{self.role}</s>\n<|user|>\n{task_input}</s>\n<|assistant|>"
        print(f"[{self.name}] 🧠 Generating Answer...")
        try:
            output = self.pipe(prompt)[0]['generated_text']
            answer = output.split("<|assistant|>")[-1].strip()
        except Exception as e:
            answer = f"Error: {e}"
        
        print(f"[{self.name}] 🗣️ Answer: {answer}")
        return answer

    def _use_calculator_tool(self, query):
        try:
            math_expression = query.lower().replace("calculate", "").replace("please", "").strip()
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
        print(f"[{self.name}] 📤 Result sent.\n")

if __name__ == "__main__":
    my_agent = Agent(name="IntelWorker-1", role="You are a helpful AI assistant.")
    my_agent.start_listening()