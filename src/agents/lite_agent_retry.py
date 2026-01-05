"""
Lite Agent with retry logic and task dependency support.
"""

import json
import time
from datetime import datetime, timedelta
from kafka import KafkaConsumer, KafkaProducer

from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_VERSION,
    KAFKA_PENDING_TOPIC, KAFKA_COMPLETED_TOPIC, KAFKA_GROUP_ID
)
from src.logging import setup_logger, metrics_collector
from src.database import get_session, close_session
from src.database.models import TaskModel, TaskStatus, AgentModel, TaskPriority


class LiteAgentWithRetry:
    """Enhanced Lite Agent with retry logic and dependency tracking."""
    
    def __init__(self, name: str):
        self.name = name
        self.agent_id = f"agent_{name.lower().replace(' ', '_')}"
        self.logger = setup_logger(f"Agent.{self.name}")
        
        # Kafka setup
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
        self.logger.info(f"✅ Ready (Lite Mode - Enhanced with Retry & Dependencies)")

    def check_dependencies(self, task_id: str) -> bool:
        """Check if all dependent tasks are completed."""
        session = get_session()
        try:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task or not task.depends_on:
                return True  # No dependencies
            
            depends_on_ids = [tid.strip() for tid in task.depends_on.split(',')]
            
            for dep_id in depends_on_ids:
                dep_task = session.query(TaskModel).filter(TaskModel.id == dep_id).first()
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    self.logger.info(f"⏳ Task {task_id} waiting for dependency {dep_id}")
                    return False
            
            return True  # All dependencies satisfied
        finally:
            close_session(session)

    def should_retry(self, task_id: str) -> bool:
        """Check if task should be retried."""
        session = get_session()
        try:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task:
                return False
            
            max_retries = task.max_retries or 3
            if task.retry_count >= max_retries:
                self.logger.warn(f"❌ Task {task_id} exceeded max retries ({max_retries})")
                return False
            
            return True
        finally:
            close_session(session)

    def schedule_retry(self, task_id: str, backoff_multiplier: int = 2) -> None:
        """Schedule task for retry with exponential backoff."""
        session = get_session()
        try:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task:
                # Calculate backoff: 5s, 10s, 20s, ...
                backoff_seconds = 5 * (backoff_multiplier ** task.retry_count)
                retry_time = datetime.utcnow() + timedelta(seconds=backoff_seconds)
                
                task.status = TaskStatus.RETRYING
                task.next_retry_time = retry_time
                session.commit()
                
                self.logger.info(f"🔄 Scheduling retry for {task_id} in {backoff_seconds}s")
        finally:
            close_session(session)

    def start_listening(self):
        """Main listening loop with retry and dependency handling."""
        self.logger.info(f"👂 Listening for tasks...")
        
        # Periodically check for scheduled retries
        import threading
        retry_thread = threading.Thread(target=self._process_scheduled_retries, daemon=True)
        retry_thread.start()
        
        for message in self.consumer:
            task_data = message.value
            task_id = task_data['id']
            description = task_data['description']
            is_retry = task_data.get('retry', False)
            
            # Check dependencies
            if not is_retry and not self.check_dependencies(task_id):
                self.logger.info(f"⏸️ Skipping {task_id} - dependencies not met")
                continue
            
            self.logger.info(f"📨 Processing {task_id}: {description}")
            
            try:
                start_time = datetime.utcnow()
                result = self.process_task(description)
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                self.send_result(task_id, result, execution_time, success=True)
                metrics_collector.record_task_completed(execution_time)
                self.logger.info(f"✅ Task {task_id} completed in {execution_time:.2f}s")
                
            except Exception as e:
                self.logger.error(f"❌ Task {task_id} failed: {str(e)}")
                
                if self.should_retry(task_id):
                    self.schedule_retry(task_id)
                    self.logger.info(f"🔄 Task {task_id} scheduled for retry")
                else:
                    self.send_result(task_id, f"Error: {str(e)}", 0, success=False)
                    self.logger.error(f"💀 Task {task_id} failed permanently")

    def _process_scheduled_retries(self):
        """Background task to process scheduled retries."""
        while True:
            try:
                time.sleep(10)  # Check every 10 seconds
                session = get_session()
                try:
                    # Find tasks ready to retry
                    now = datetime.utcnow()
                    retry_tasks = session.query(TaskModel).filter(
                        TaskModel.status == TaskStatus.RETRYING,
                        TaskModel.next_retry_time <= now
                    ).all()
                    
                    for task in retry_tasks:
                        self.logger.info(f"⏰ Retrying {task.id}")
                        task.status = TaskStatus.PENDING
                        task.next_retry_time = None
                        session.commit()
                        
                        # Re-queue to Kafka
                        payload = {
                            "id": task.id,
                            "description": task.description,
                            "priority": task.priority.value if task.priority else "normal",
                            "retry": True
                        }
                        self.producer.send(KAFKA_PENDING_TOPIC, value=payload)
                    
                    if retry_tasks:
                        self.producer.flush()
                finally:
                    close_session(session)
            except Exception as e:
                self.logger.error(f"Error in retry processor: {str(e)}")

    def process_task(self, task_input: str) -> str:
        """Process task and return result."""
        
        # 1. CALCULATOR TOOL
        if "calculate" in task_input.lower():
            return self._use_calculator_tool(task_input)
        
        # 2. TEXT ANALYSIS TOOL
        if "analyze text" in task_input.lower() or "count words" in task_input.lower():
            return self._use_text_analysis_tool(task_input)
        
        # 3. STRING MANIPULATION TOOL
        if any(op in task_input.lower() for op in ["uppercase", "lowercase", "reverse"]):
            return self._use_string_tool(task_input)
        
        # 4. DATA SUMMARIZATION TOOL
        if "summarize" in task_input.lower():
            return self._use_summarization_tool(task_input)
        
        return "Unknown task. Supported: calculate, analyze text, uppercase/lowercase/reverse, summarize"

    def _use_calculator_tool(self, task_input: str) -> str:
        try:
            expr = task_input.replace("calculate", "").strip()
            result = eval(expr)
            return f"Result: {result}"
        except:
            return "Error in calculation"

    def _use_text_analysis_tool(self, task_input: str) -> str:
        text = task_input.replace("analyze text", "").replace("count words", "").strip()
        words = len(text.split())
        chars = len(text)
        sentences = len(text.split('.'))
        avg_word_length = sum(len(w) for w in text.split()) / max(words, 1)
        return f"{words} words, {chars} chars, {sentences} sentences, avg word length {avg_word_length:.1f}"

    def _use_string_tool(self, task_input: str) -> str:
        if "uppercase" in task_input.lower():
            text = task_input.replace("uppercase", "").strip()
            return f"Uppercase: {text.upper()}"
        elif "lowercase" in task_input.lower():
            text = task_input.replace("lowercase", "").strip()
            return f"Lowercase: {text.lower()}"
        elif "reverse" in task_input.lower():
            text = task_input.replace("reverse", "").strip()
            return f"Reversed: {text[::-1]}"
        return "Invalid string operation"

    def _use_summarization_tool(self, task_input: str) -> str:
        text = task_input.replace("summarize", "").strip()
        first_sentence = text.split('.')[0] + '.'
        return f"Summary: {first_sentence} ({len(text)} chars, {len(text.split())} words)"

    def send_result(self, task_id: str, result: str, execution_time: float, success: bool = True):
        """Send result to database and Kafka."""
        session = get_session()
        try:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = result if success else None
                task.error = None if success else result
                task.execution_time = execution_time
                task.completed_at = datetime.utcnow()
                task.assigned_agent = self.agent_id
                session.commit()
                
                # Send to completed topic
                payload = {
                    "id": task_id,
                    "result": result,
                    "execution_time": execution_time,
                    "success": success
                }
                self.producer.send(KAFKA_COMPLETED_TOPIC, value=payload)
                self.producer.flush()
        finally:
            close_session(session)


def run_lite_agent_with_retry(name: str = "Lite Agent"):
    """Run the lite agent with retry support."""
    agent = LiteAgentWithRetry(name)
    try:
        agent.start_listening()
    except KeyboardInterrupt:
        print("\n👋 Agent stopped")


if __name__ == '__main__':
    run_lite_agent_with_retry()
