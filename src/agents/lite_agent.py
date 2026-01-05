import json
import time
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer

from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_VERSION,
    KAFKA_PENDING_TOPIC, KAFKA_COMPLETED_TOPIC, KAFKA_GROUP_ID
)
from src.logging import setup_logger, metrics_collector
from src.database import get_session, close_session
from src.database.models import TaskModel, TaskStatus, AgentModel

class LiteAgent:
    def __init__(self, name: str):
        self.name = name
        self.agent_id = f"agent_{name.lower().replace(' ', '_')}"
        self.logger = setup_logger(f"Agent.{self.name}")
        
        # Connect to Kafka (Standard Setup)
        self.logger.info(f"🔌 Connecting to Kafka...")
        self.consumer = KafkaConsumer(
            KAFKA_PENDING_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            api_version=KAFKA_API_VERSION,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=KAFKA_GROUP_ID,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            api_version=KAFKA_API_VERSION,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        self.logger.info(f"✅ Ready (Lite Mode - No Heavy AI Model)")

    def start_listening(self):
        self.logger.info(f"👂 Listening for tasks...")
        for message in self.consumer:
            task_data = message.value
            task_id = task_data['id']
            self.logger.info(f"📨 Picked up task {task_id}: {task_data['description']}")
            
            start_time = datetime.utcnow()
            result = self.process_task(task_data['description'])
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.send_result(task_id, result, execution_time)
            metrics_collector.record_task_completed(execution_time)

    def process_task(self, task_input):
        # 1. CALCULATOR TOOL
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

        # 5. FALLBACK (Since we have no Brain in Lite Mode)
        return "I am a Lite Agent. I can: calculate, analyze text, manipulate strings, or summarize data."

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
        self.logger.info(f"🔢 Tool Output: {response}")
        return response

    def _use_text_analysis_tool(self, query: str) -> str:
        """Analyze text: word count, sentence count, etc."""
        try:
            # Extract text after keywords
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
            
            # Simple summarization: first sentence + stats
            sentences = [s.strip() for s in text.split(".") if s.strip()]
            first_sentence = sentences[0] if sentences else text[:50]
            
            response = f"Summary: {first_sentence}... (Total: {len(sentences)} sentences, {len(text)} chars)"
        except Exception as e:
            response = f"Error: {e}"
        self.logger.info(f"📋 Tool Output: {response}")
        return response

    def send_result(self, task_id, result, execution_time: float = 0.0):
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
        
        self.logger.info(f"📤 Result sent back ({execution_time:.2f}s)")

if __name__ == "__main__":
    agent = LiteAgent(name="LiteWorker-1")
    agent.start_listening()