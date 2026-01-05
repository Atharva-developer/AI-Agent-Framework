"""
Batch upload and advanced task management endpoints.
"""

import uuid
import json
import io
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile, File
from pydantic import BaseModel
import pandas as pd

from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_PENDING_TOPIC
from src.logging import setup_logger, metrics_collector
from src.database import get_session, close_session
from src.database.models import TaskModel, TaskStatus, TaskPriority
from kafka import KafkaProducer

logger = setup_logger(__name__)
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)


class BatchTaskRequest(BaseModel):
    """Model for tasks in batch upload."""
    description: str
    priority: Optional[str] = "normal"
    scheduled_time: Optional[str] = None
    depends_on: Optional[str] = None
    max_retries: Optional[int] = 3


class BatchUploadResponse(BaseModel):
    """Response for batch upload."""
    batch_id: str
    total_tasks: int
    created_tasks: int
    failed_tasks: int
    errors: List[dict]


class ScheduledTaskRequest(BaseModel):
    """Request to schedule a task."""
    description: str
    scheduled_time: str  # ISO format datetime
    priority: Optional[str] = "normal"
    depends_on: Optional[str] = None


async def process_csv_upload(file: UploadFile, user_id: str) -> BatchUploadResponse:
    """Process CSV file upload with multiple tasks."""
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    errors = []
    created_count = 0
    failed_count = 0
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        session = get_session()
        try:
            for idx, row in df.iterrows():
                try:
                    # Parse row data
                    description = row.get('description', '').strip()
                    if not description:
                        errors.append({
                            "row": idx + 2,
                            "error": "Missing description field"
                        })
                        failed_count += 1
                        continue
                    
                    priority_str = str(row.get('priority', 'normal')).lower()
                    try:
                        priority = TaskPriority[priority_str.upper()]
                    except KeyError:
                        priority = TaskPriority.NORMAL
                    
                    # Create task
                    task_id = f"task_{uuid.uuid4().hex[:12]}"
                    scheduled_time = None
                    if pd.notna(row.get('scheduled_time')):
                        try:
                            scheduled_time = datetime.fromisoformat(str(row['scheduled_time']))
                        except:
                            pass
                    
                    task = TaskModel(
                        id=task_id,
                        description=description,
                        priority=priority,
                        status=TaskStatus.SCHEDULED if scheduled_time else TaskStatus.PENDING,
                        batch_id=batch_id,
                        scheduled_time=scheduled_time,
                        depends_on=row.get('depends_on'),
                        max_retries=int(row.get('max_retries', 3)),
                        created_at=datetime.utcnow()
                    )
                    session.add(task)
                    
                    # Send to Kafka if not scheduled
                    if not scheduled_time:
                        payload = {
                            "id": task_id,
                            "description": description,
                            "priority": priority.value,
                            "batch_id": batch_id
                        }
                        producer.send(KAFKA_PENDING_TOPIC, value=payload)
                    
                    created_count += 1
                    logger.info(f"Created task {task_id} from batch {batch_id}")
                    
                except Exception as e:
                    errors.append({
                        "row": idx + 2,
                        "error": str(e)
                    })
                    failed_count += 1
            
            session.commit()
            producer.flush()
            metrics_collector.record_batch_uploaded(created_count)
            logger.info(f"Batch {batch_id}: {created_count} created, {failed_count} failed")
            
        finally:
            close_session(session)
    
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV processing error: {str(e)}"
        )
    
    return BatchUploadResponse(
        batch_id=batch_id,
        total_tasks=created_count + failed_count,
        created_tasks=created_count,
        failed_tasks=failed_count,
        errors=errors
    )


async def process_json_upload(tasks: List[BatchTaskRequest], user_id: str) -> BatchUploadResponse:
    """Process JSON array of tasks."""
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    errors = []
    created_count = 0
    
    session = get_session()
    try:
        for idx, task_req in enumerate(tasks):
            try:
                priority = TaskPriority[task_req.priority.upper()]
            except (KeyError, AttributeError):
                priority = TaskPriority.NORMAL
            
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            scheduled_time = None
            if task_req.scheduled_time:
                try:
                    scheduled_time = datetime.fromisoformat(task_req.scheduled_time)
                except:
                    pass
            
            task = TaskModel(
                id=task_id,
                description=task_req.description,
                priority=priority,
                status=TaskStatus.SCHEDULED if scheduled_time else TaskStatus.PENDING,
                batch_id=batch_id,
                scheduled_time=scheduled_time,
                depends_on=task_req.depends_on,
                max_retries=task_req.max_retries or 3,
                created_at=datetime.utcnow()
            )
            session.add(task)
            
            if not scheduled_time:
                payload = {
                    "id": task_id,
                    "description": task_req.description,
                    "priority": priority.value,
                    "batch_id": batch_id
                }
                producer.send(KAFKA_PENDING_TOPIC, value=payload)
            
            created_count += 1
        
        session.commit()
        producer.flush()
        metrics_collector.record_batch_uploaded(created_count)
        logger.info(f"JSON batch {batch_id}: {created_count} tasks created")
        
    except Exception as e:
        logger.error(f"JSON batch error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JSON processing error: {str(e)}"
        )
    finally:
        close_session(session)
    
    return BatchUploadResponse(
        batch_id=batch_id,
        total_tasks=created_count,
        created_tasks=created_count,
        failed_tasks=0,
        errors=errors
    )


async def schedule_task(task_req: ScheduledTaskRequest, user_id: str) -> dict:
    """Schedule a task to run at a specific time."""
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    
    try:
        scheduled_time = datetime.fromisoformat(task_req.scheduled_time)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
        )
    
    if scheduled_time < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future"
        )
    
    try:
        priority = TaskPriority[task_req.priority.upper()]
    except KeyError:
        priority = TaskPriority.NORMAL
    
    session = get_session()
    try:
        task = TaskModel(
            id=task_id,
            description=task_req.description,
            priority=priority,
            status=TaskStatus.SCHEDULED,
            scheduled_time=scheduled_time,
            depends_on=task_req.depends_on,
            created_at=datetime.utcnow()
        )
        session.add(task)
        session.commit()
        logger.info(f"Task {task_id} scheduled for {scheduled_time}")
        
        return {
            "task_id": task_id,
            "status": "scheduled",
            "scheduled_time": scheduled_time.isoformat()
        }
    finally:
        close_session(session)
