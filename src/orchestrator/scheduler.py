"""
Task Scheduler Service - Processes scheduled tasks and moves them to pending.
"""

import json
import time
from datetime import datetime
from kafka import KafkaProducer
from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_VERSION,
    KAFKA_PENDING_TOPIC
)
from src.logging import setup_logger
from src.database import get_session, close_session
from src.database.models import TaskModel, TaskStatus, TaskPriority

logger = setup_logger(__name__)

class TaskScheduler:
    """APScheduler-based task scheduling service."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(daemon=True)
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            api_version=KAFKA_API_VERSION,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        logger.info("📅 Task Scheduler initialized")

    def start(self):
        """Start the scheduler service."""
        # Add job to check scheduled tasks every 30 seconds
        self.scheduler.add_job(
            self._process_scheduled_tasks,
            'interval',
            seconds=30,
            id='scheduled_task_processor',
            name='Process Scheduled Tasks'
        )
        
        self.scheduler.start()
        logger.info("✅ Task Scheduler started")

    def _process_scheduled_tasks(self):
        """Check and process tasks that are scheduled to run."""
        session = get_session()
        try:
            now = datetime.utcnow()
            
            # Find all tasks that are scheduled and ready to run
            scheduled_tasks = session.query(TaskModel).filter(
                TaskModel.status == TaskStatus.SCHEDULED,
                TaskModel.scheduled_time <= now
            ).all()
            
            for task in scheduled_tasks:
                try:
                    # Move task to pending status
                    task.status = TaskStatus.PENDING
                    session.commit()
                    
                    # Send to Kafka
                    payload = {
                        "id": task.id,
                        "description": task.description,
                        "priority": task.priority.value if task.priority else "normal",
                        "batch_id": task.batch_id,
                        "scheduled": True
                    }
                    self.producer.send(KAFKA_PENDING_TOPIC, value=payload)
                    
                    logger.info(f"⏰ Scheduled task {task.id} moved to pending")
                except Exception as e:
                    logger.error(f"Error processing scheduled task {task.id}: {str(e)}")
            
            if scheduled_tasks:
                self.producer.flush()
                logger.info(f"📤 Processed {len(scheduled_tasks)} scheduled tasks")
                
        except Exception as e:
            logger.error(f"Error in task scheduler: {str(e)}")
        finally:
            close_session(session)

    def stop(self):
        """Stop the scheduler service."""
        self.scheduler.shutdown()
        logger.info("⛔ Task Scheduler stopped")


def run_scheduler():
    """Run the scheduler as a standalone service."""
    scheduler = TaskScheduler()
    scheduler.start()
    
    try:
        # Keep the scheduler running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped")
        scheduler.stop()


if __name__ == '__main__':
    run_scheduler()
