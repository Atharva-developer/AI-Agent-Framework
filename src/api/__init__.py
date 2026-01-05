from src.database.models import TaskModel, TaskStatus, AgentModel, UserModel, TaskPriority
"""
REST API endpoints for the AI Agent Framework.
"""

import uuid
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from kafka import KafkaProducer
import time

from config import (
    API_HOST, API_PORT, KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_PENDING_TOPIC, API_KEY_ENABLED
)
from src.logging import setup_logger, metrics_collector
from src.database import init_db, get_session, close_session
from src.database.models import TaskModel, TaskStatus, AgentModel, UserModel, TaskPriority
from src.load_balancer import load_balancer
from src.api.security import verify_api_key, verify_permission
from src.api.batch import process_csv_upload, process_json_upload, schedule_task, BatchTaskRequest, ScheduledTaskRequest, BatchUploadResponse
from src.api.realtime import start_realtime_listener, manager as ws_manager
from fastapi import WebSocket
from src.api.batch import process_csv_upload, process_json_upload, schedule_task, BatchTaskRequest, ScheduledTaskRequest, BatchUploadResponse

logger = setup_logger(__name__)
app = FastAPI(title="AI Agent Framework API", version="1.0.0")

# Initialize database
init_db()

# Start realtime Kafka -> WebSocket listener
try:
    start_realtime_listener()
except Exception:
    logger.warning("Realtime listener failed to start")

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)


# ============ Pydantic Models ============

class TaskRequest(BaseModel):
    description: str
    workflow_id: Optional[str] = None
    priority: Optional[str] = "normal"
    depends_on: Optional[str] = None
    scheduled_time: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    description: str
    status: str
    assigned_agent: Optional[str]
    result: Optional[str]
    created_at: str
    completed_at: Optional[str]
    priority: Optional[str]
    depends_on: Optional[str]


class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    status: str
    tasks_completed: int
    tasks_failed: int
    avg_latency_ms: Optional[float]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    agents_online: int
    tasks_pending: int


class MetricsResponse(BaseModel):
    tasks_submitted: int
    tasks_completed: int
    tasks_failed: int
    agents_online: int
    avg_latency_ms: float
    timestamp: str


# ============ Endpoints ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    session = get_session()
    try:
        agents_online = session.query(AgentModel).filter(
            AgentModel.status == "online"
        ).count()
        tasks_pending = session.query(TaskModel).filter(
            TaskModel.status == TaskStatus.PENDING
        ).count()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            agents_online=agents_online,
            tasks_pending=tasks_pending
        )
    finally:
        close_session(session)


@app.post("/tasks", response_model=TaskResponse)
async def submit_task(
    task_request: TaskRequest,
    user_id: str = Depends(verify_api_key)
):
    """
    Submit a new task to the framework.
    
    Args:
        task_request: Task description and optional workflow ID
        user_id: Authenticated user ID
    
    Returns:
        Created task details
    """
    # Check permission
    if not await verify_permission(user_id, "submit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'submit' permission"
        )

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    session = get_session()

    try:
        # Determine priority
        try:
            priority = TaskPriority[task_request.priority.upper()]
        except Exception:
            priority = TaskPriority.NORMAL

        # Parse scheduled_time if provided
        scheduled_time = None
        if task_request.scheduled_time:
            try:
                scheduled_time = datetime.fromisoformat(task_request.scheduled_time)
            except Exception:
                scheduled_time = None

        # Create task record
        task = TaskModel(
            id=task_id,
            description=task_request.description,
            status=TaskStatus.SCHEDULED if scheduled_time else TaskStatus.PENDING,
            workflow_id=task_request.workflow_id,
            priority=priority,
            depends_on=task_request.depends_on,
            scheduled_time=scheduled_time,
            created_at=datetime.utcnow()
        )
        session.add(task)
        session.commit()

        # Send to Kafka
        if not scheduled_time:
            payload = {
                "id": task_id,
                "description": task_request.description,
                "workflow_id": task_request.workflow_id,
                "priority": priority.value,
                "depends_on": task_request.depends_on
            }
            producer.send(KAFKA_PENDING_TOPIC, value=payload)
            producer.flush()

        metrics_collector.record_task_submitted()
        logger.info(f"Task {task_id} submitted by user {user_id}")

        return TaskResponse(
            id=task.id,
            description=task.description,
            status=task.status.value,
            assigned_agent=task.assigned_agent,
            result=task.result,
            created_at=task.created_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            priority=task.priority.value if task.priority else None,
            depends_on=task.depends_on
        )

    finally:
        close_session(session)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user_id: str = Depends(verify_api_key)
):
    """
    Get task status and results.
    
    Args:
        task_id: Task ID
        user_id: Authenticated user ID
    
    Returns:
        Task details
    """
    if not await verify_permission(user_id, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'read' permission"
        )

    session = get_session()
    try:
        task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse(
            id=task.id,
            description=task.description,
            status=task.status.value,
            assigned_agent=task.assigned_agent,
            result=task.result,
            created_at=task.created_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None
        )
    finally:
        close_session(session)


@app.get("/agents", response_model=List[AgentInfo])
async def list_agents(
    user_id: str = Depends(verify_api_key)
):
    """
    List all registered agents.
    
    Returns:
        List of agent information
    """
    if not await verify_permission(user_id, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'read' permission"
        )

    session = get_session()
    try:
        agents = session.query(AgentModel).all()
        return [
            AgentInfo(
                id=agent.id,
                name=agent.name,
                role=agent.role,
                status=agent.status,
                tasks_completed=agent.tasks_completed,
                tasks_failed=agent.tasks_failed,
                avg_latency_ms=agent.avg_latency_ms
            )
            for agent in agents
        ]
    finally:
        close_session(session)


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    user_id: str = Depends(verify_api_key)
):
    """
    Get system metrics.
    
    Returns:
        System metrics and statistics
    """
    if not await verify_permission(user_id, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'read' permission"
        )

    metrics = metrics_collector.get_metrics()
    return MetricsResponse(**metrics)


@app.post("/agents/register")
async def register_agent(
    agent_id: str,
    name: str,
    role: str,
    model_id: Optional[str] = None
):
    """
    Register a new agent.
    
    Args:
        agent_id: Unique agent identifier
        name: Agent name
        role: Agent role/description
        model_id: Optional model identifier
    """
    session = get_session()
    try:
        existing = session.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if existing:
            existing.status = "online"
            existing.last_heartbeat = datetime.utcnow()
            session.commit()
            logger.info(f"Agent {agent_id} re-registered")
        else:
            agent = AgentModel(
                id=agent_id,
                name=name,
                role=role,
                model_id=model_id,
                status="online",
                last_heartbeat=datetime.utcnow()
            )
            session.add(agent)
            session.commit()
            metrics_collector.record_agent_online(agent_id)
            logger.info(f"Agent {agent_id} registered")

        return {"status": "registered", "agent_id": agent_id}

    finally:
        close_session(session)


@app.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
    """
    Agent heartbeat for health check.
    
    Args:
        agent_id: Agent identifier
    """
    session = get_session()
    try:
        agent = session.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if agent:
            agent.last_heartbeat = datetime.utcnow()
            agent.status = "online"
            session.commit()
            return {"status": "acknowledged"}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
    finally:
        close_session(session)


# ============ Advanced Task Management Endpoints ============

@app.post("/batch/upload/csv", response_model=BatchUploadResponse)
async def upload_csv_batch(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_api_key)
):
    """Upload CSV file with multiple tasks."""
    if not await verify_permission(user_id, "submit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'submit' permission"
        )
    return await process_csv_upload(file, user_id)


@app.post("/batch/upload/json", response_model=BatchUploadResponse)
async def upload_json_batch(
    tasks: List[BatchTaskRequest],
    user_id: str = Depends(verify_api_key)
):
    """Upload JSON array of tasks."""
    if not await verify_permission(user_id, "submit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'submit' permission"
        )
    return await process_json_upload(tasks, user_id)


@app.post("/tasks/schedule", response_model=dict)
async def schedule_task_endpoint(
    task_req: ScheduledTaskRequest,
    user_id: str = Depends(verify_api_key)
):
    """Schedule a task to run at a specific time."""
    if not await verify_permission(user_id, "submit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'submit' permission"
        )
    return await schedule_task(task_req, user_id)


@app.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str,
    user_id: str = Depends(verify_api_key)
):
    """Manually retry a failed task."""
    if not await verify_permission(user_id, "submit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'submit' permission"
        )
    session = get_session()
    try:
        task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status != TaskStatus.FAILED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot retry task with status {task.status.value}")
        task.status = TaskStatus.PENDING
        task.retry_count = (task.retry_count or 0) + 1
        task.next_retry_time = None
        session.commit()
        payload = {"id": task_id, "description": task.description, "priority": task.priority.value if task.priority else "normal", "retry": True}
        producer.send(KAFKA_PENDING_TOPIC, value=payload)
        producer.flush()
        return {"task_id": task_id, "status": "pending", "retry_count": task.retry_count}
    finally:
        close_session(session)


@app.get("/batch/{batch_id}/tasks")
async def get_batch_tasks(
    batch_id: str,
    user_id: str = Depends(verify_api_key)
):
    """Get all tasks in a batch."""
    if not await verify_permission(user_id, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks 'read' permission"
        )
    session = get_session()
    try:
        tasks = session.query(TaskModel).filter(TaskModel.batch_id == batch_id).all()
        return {
            "batch_id": batch_id,
            "total_tasks": len(tasks),
            "tasks": [{"id": t.id, "description": t.description, "status": t.status.value, "priority": t.priority.value if t.priority else "normal"} for t in tasks]
        }
    finally:
        close_session(session)


@app.get("/metrics/advanced")
async def get_advanced_metrics(
    user_id: str = Depends(verify_api_key)
):
    """Get advanced metrics including priority distribution and retry stats."""
    if not await verify_permission(user_id, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User lacks 'read' permission")
    session = get_session()
    try:
        total_tasks = session.query(TaskModel).count()
        completed = session.query(TaskModel).filter(TaskModel.status == TaskStatus.COMPLETED).count()
        failed = session.query(TaskModel).filter(TaskModel.status == TaskStatus.FAILED).count()
        scheduled = session.query(TaskModel).filter(TaskModel.status == TaskStatus.SCHEDULED).count()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "task_summary": {"total": total_tasks, "completed": completed, "failed": failed, "scheduled": scheduled},
            "agent_stats": {"online": session.query(AgentModel).filter(AgentModel.status == "online").count()}
        }
    finally:
        close_session(session)

def run_api(host: str = API_HOST, port: int = API_PORT, reload: bool = False):
    """
    Run the FastAPI application.
    
    Args:
        host: Host address
        port: Port number
        reload: Enable auto-reload
    """
    import uvicorn
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)


@app.websocket('/ws/updates')
async def websocket_updates(websocket: WebSocket):
    """WebSocket endpoint for realtime updates (dashboard clients connect here)."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # keep connection alive; dashboard won't send messages normally
            await websocket.receive_text()
    except Exception:
        ws_manager.disconnect(websocket)
