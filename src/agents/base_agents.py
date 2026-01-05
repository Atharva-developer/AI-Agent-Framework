import json
import time
import torch
import json
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer

from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_VERSION,
    KAFKA_PENDING_TOPIC, KAFKA_COMPLETED_TOPIC, KAFKA_GROUP_ID
)
from src.logging import setup_logger, metrics_collector
from src.database import get_session, close_session
from src.database.models import TaskModel, TaskStatus, AgentModel

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
        self.agent_id = f"agent_{name.lower().replace(' ', '_')}"
        self.logger = setup_logger(f"Agent.{self.name}")
        
        # 1. Setup Kafka Consumer (API Version Fixed here)
        self.logger.info(f"🔌 Connecting to Kafka...")
        self.consumer = KafkaConsumer(
            KAFKA_PENDING_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=KAFKA_GROUP_ID,
            api_version=KAFKA_API_VERSION,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # 2. Setup Kafka Producer (API Version Fixed here)
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            api_version=KAFKA_API_VERSION,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )

        # 3. LOAD THE BRAIN (Safe Mode)
        self.logger.info(f"⏳ Loading AI Model ({model_id})...")
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
            self.logger.info(f"🐢 Loaded in Standard Mode (Non-Intel).")

        # Create the pipeline
        self.pipe = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer, max_new_tokens=100)
        self.logger.info(f"🧠 Brain Loaded & Ready!")

    def start_listening(self):
        self.logger.info(f"👂 Listening for tasks on Kafka...")
        for message in self.consumer:
            task_data = message.value
            task_id = task_data['id']
            self.logger.info(f"📨 Picked up task {task_id}: {task_data['description']}")
            
            start_time = datetime.utcnow()
            result = self.process_task(task_data['description'])
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.send_result(task_id, result, execution_time)
            metrics_collector.record_task_completed(execution_time)

    def process_task(self, task_input: str) -> str:
        # 1. TOOL USAGE: Calculator
        if "calculate" in task_input.lower():
            self.logger.info(f"🛠️ Tool Triggered: Calculator")
            return self._use_calculator_tool(task_input)
        
        # 2. TEXT ANALYSIS TOOL
        if "analyze text" in task_input.lower() or "count words" in task_input.lower():
            self.logger.info(f"🛠️ Tool Triggered: Text Analysis")
            return self._use_text_analysis_tool(task_input)
        
        # 3. STRING MANIPULATION TOOL
        if "uppercase" in task_input.lower() or "lowercase" in task_input.lower() or "reverse" in task_input.lower():
            self.logger.info(f"🛠️ Tool Triggered: String Manipulation")
            return self._use_string_tool(task_input)
        
        # 4. DATA SUMMARY TOOL
        if "summarize" in task_input.lower() or "extract" in task_input.lower():
            self.logger.info(f"🛠️ Tool Triggered: Data Summary")
            return self._use_summary_tool(task_input)

        # 5. STANDARD AI (for other tasks)
        prompt = f"<|system|>\n{self.role}</s>\n<|user|>\n{task_input}</s>\n<|assistant|>"
        self.logger.info(f"🧠 Generating Answer...")
        try:
            output = self.pipe(prompt)[0]['generated_text']
            answer = output.split("<|assistant|>")[-1].strip()
        except Exception as e:
            answer = f"Error: {e}"
            self.logger.error(answer)
        
        self.logger.info(f"🗣️ Answer: {answer}")
        return answer

    def _use_calculator_tool(self, query: str) -> str:
        try:
            math_expression = query.lower().replace("calculate", "").replace("please", "").strip()
            allowed = set("0123456789+-*/(). ")
            if not set(math_expression).issubset(allowed):
                return "Error: unsafe characters."
            result = eval(math_expression)
            response = f"Result: {result}"
        except Exception as e:
            response = f"Error: {e}"
        self.logger.info(f"🔢 Tool Output: {response}")
        return response

    def _use_text_analysis_tool(self, query: str) -> str:
        """Analyze text: word count, sentence count, etc."""
        try:
            text = query.lower().replace("analyze text", "").replace("count words", "").strip()
            if not text:
                return "Error: Please provide text to analyze."
            
            word_count = len(text.split())
            char_count = len(text)
            sentence_count = text.count(".") + text.count("!") + text.count("?")
            avg_word_length = char_count / word_count if word_count > 0 else 0
            
            response = f"Text Analysis: {word_count} words, {char_count} chars, {sentence_count} sentences, avg word length {avg_word_length:.1f}"
        except Exception as e:
            response = f"Error: {e}"
        self.logger.info(f"📊 Tool Output: {response}")
        return response

    def _use_string_tool(self, query: str) -> str:
        """String manipulation: uppercase, lowercase, reverse."""
        try:
            if "uppercase" in query.lower():
                text = query.lower().replace("uppercase", "").strip()
                result = text.upper()
                response = f"Uppercase: {result}"
            elif "lowercase" in query.lower():
                text = query.lower().replace("lowercase", "").strip()
                result = text.lower()
                response = f"Lowercase: {result}"
            elif "reverse" in query.lower():
                text = query.lower().replace("reverse", "").strip()
                result = text[::-1]
                response = f"Reversed: {result}"
            else:
                response = "Error: Unknown string operation."
        except Exception as e:
            response = f"Error: {e}"
        self.logger.info(f"📝 Tool Output: {response}")
        return response

    def _use_summary_tool(self, query: str) -> str:
        """Summarize or extract key info from text."""
        try:
            text = query.lower().replace("summarize", "").replace("extract", "").strip()
            if not text:
                return "Error: Please provide text to summarize."
            
            sentences = [s.strip() for s in text.split(".") if s.strip()]
            first_sentence = sentences[0] if sentences else text[:50]
            
            response = f"Summary: {first_sentence}... (Total: {len(sentences)} sentences, {len(text)} chars)"
        except Exception as e:
            response = f"Error: {e}"
        self.logger.info(f"📋 Tool Output: {response}")
        return response

    def send_result(self, task_id: str, result: str, execution_time: float = 0.0):
        result_payload = {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "agent": self.name,
            "execution_time": execution_time
        }
        self.producer.send(KAFKA_COMPLETED_TOPIC, value=result_payload)
        self.producer.flush()
        
        # Update database
        session = get_session()
        try:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.assigned_agent = self.agent_id
                task.completed_at = datetime.utcnow()
                task.execution_time = execution_time
                session.commit()
                
                # Update agent metrics
                agent = session.query(AgentModel).filter(AgentModel.id == self.agent_id).first()
                if agent:
                    agent.tasks_completed += 1
                    agent.last_heartbeat = datetime.utcnow()
                    session.commit()
        except Exception as e:
            self.logger.error(f"Failed to update database: {e}")
        finally:
            close_session(session)
        
        self.logger.info(f"📤 Result sent ({execution_time:.2f}s)")

if __name__ == "__main__":
    my_agent = Agent(name="IntelWorker-1", role="You are a helpful AI assistant.")
    my_agent.start_listening()