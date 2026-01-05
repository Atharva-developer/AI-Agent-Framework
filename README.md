# Intel AI Agent Framework — Enhanced Edition

A production-ready Kafka-driven distributed agent architecture with **database persistence**, **REST API**, **authentication**, **load balancing**, and **monitoring**.

## 🎯 Features

- **Kafka-based task queue** — Async task distribution to agents
- **Persistent database** — SQLite/PostgreSQL task history, metrics, agents, workflows
- **REST API** — Submit tasks, query status, list agents, get metrics
- **API key authentication** — Secure endpoints with role-based permissions
- **Agent load balancing** — Round-robin, least-busy, or random strategies
- **Structured logging & monitoring** — Real-time metrics collection
- **Two agent types** — Full-featured (with LLM) and lightweight (calculator only)
- **Dashboard** — Terminal and web interfaces for monitoring

## 📁 Project Structure

```
.
├── config.py                          # Centralized configuration
├── run_api.py                         # Start REST API server
├── run_agent.py                       # Start full agent
├── run_lite_agent.py                  # Start lightweight agent
├── requirements.txt                   # Python dependencies
├── docker-compose.yml                 # Kafka + Zookeeper
│
├── src/
│   ├── agents/
│   │   ├── base_agents.py            # Full-featured agent with LLM
│   │   └── lite_agent.py             # Lightweight agent (no model)
│   │
│   ├── api/
│   │   ├── __init__.py               # FastAPI app + endpoints
│   │   └── security.py               # API key authentication
│   │
│   ├── database/
│   │   ├── __init__.py               # DB initialization
│   │   └── models.py                 # SQLAlchemy models
│   │
│   ├── load_balancer/
│   │   └── __init__.py               # Load balancing strategies
│   │
│   ├── logging/
│   │   └── __init__.py               # Logging & metrics
│   │
│   ├── orchestrator/
│   │   ├── manager.py                # Task producer
│   │   └── workflow_engine.py        # Multi-step workflows
│   │
│   └── dashboard/
│       ├── term_dash.py              # Terminal dashboard
│       └── web_app.py                # Flask web dashboard
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (optional — config.py has sensible defaults)
cat > .env <<'EOF'
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
DATABASE_URL=sqlite:///./agent_framework.db
API_KEY_ENABLED=True
LOG_LEVEL=INFO
EOF
```

### 2. Start Kafka

```bash
docker-compose up -d
```

### 3. Create database and default user

```bash
python3 -c "
from src.database import init_db, get_session, close_session
from src.database.models import UserModel
import uuid

init_db()

session = get_session()
user = UserModel(
    id=str(uuid.uuid4()),
    username='admin',
    api_key='sk-default-admin-key',
    is_active='active',
    permissions='admin'
)
session.add(user)
session.commit()
close_session(session)
print('✅ Database initialized. Default user: admin, API key: sk-default-admin-key')
"
```

### 4. Start API server (in one terminal)

```bash
python3 run_api.py
# API available at http://127.0.0.1:8000
# Docs: http://127.0.0.1:8000/docs
```

### 5. Start agent(s) (in separate terminals)

```bash
# Full-featured agent (requires torch/transformers)
python3 run_agent.py

# OR lightweight agent (no heavy dependencies)
python3 run_lite_agent.py
```

### 6. Test via API

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Authorization: Bearer sk-default-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"description": "calculate 10 + 5"}'

# Get task status
curl http://127.0.0.1:8000/tasks/task_xxxxx \
  -H "Authorization: Bearer sk-default-admin-key"

# List agents
curl http://127.0.0.1:8000/agents \
  -H "Authorization: Bearer sk-default-admin-key"

# Get metrics
curl http://127.0.0.1:8000/metrics \
  -H "Authorization: Bearer sk-default-admin-key"
```

### 7. Monitor (optional)

```bash
# Terminal dashboard
python3 src/dashboard/term_dash.py

# Web dashboard (Flask)
python3 src/dashboard/web_app.py
# Open http://127.0.0.1:5000
```

## 🔑 API Endpoints

### Authentication
All endpoints (except `/health`) require `Authorization: Bearer <API_KEY>` header.

### Core Endpoints

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| `POST` | `/tasks` | Submit a new task | `submit` |
| `GET` | `/tasks/{task_id}` | Get task status and result | `read` |
| `GET` | `/agents` | List all agents | `read` |
| `GET` | `/metrics` | Get system metrics | `read` |
| `GET` | `/health` | System health check | *public* |

### Agent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/agents/register` | Register/heartbeat an agent |
| `POST` | `/agents/{agent_id}/heartbeat` | Agent health check |

## 📊 Configuration

Edit `.env` or pass environment variables to customize:

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_PENDING_TOPIC=pending_tasks
KAFKA_COMPLETED_TOPIC=completed_tasks

# Database
DATABASE_URL=sqlite:///./agent_framework.db
# DATABASE_URL=postgresql://user:password@localhost/agent_db

# API
API_HOST=127.0.0.1
API_PORT=8000
API_KEY_ENABLED=True

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/agent_framework.log

# Load Balancer
LOAD_BALANCER_STRATEGY=round_robin  # round_robin, least_busy, random
AGENT_HEALTH_CHECK_INTERVAL=30

# Monitoring
METRICS_ENABLED=True
```

## 🔐 Security

### API Keys
- Enable with `API_KEY_ENABLED=True` (default)
- Pass key via header: `Authorization: Bearer <KEY>`
- Manage in database (`UserModel`)
- Set `is_active='active'` to enable user

### Permissions
- `read` — Query tasks, agents, metrics
- `submit` — Create new tasks
- `admin` — All permissions

### Example: Add New User

```python
from src.database import get_session, close_session
from src.database.models import UserModel
import uuid

session = get_session()
user = UserModel(
    id=str(uuid.uuid4()),
    username='data-scientist',
    api_key='sk-data-scientist-key',
    is_active='active',
    permissions='read,submit'
)
session.add(user)
session.commit()
close_session(session)
```

## 📈 Monitoring & Metrics

Access metrics via API:

```json
{
  "tasks_submitted": 42,
  "tasks_completed": 40,
  "tasks_failed": 2,
  "agents_online": 2,
  "agents_offline": 0,
  "avg_latency_ms": 1234.5,
  "total_execution_time": 49380.0,
  "timestamp": "2026-01-05T12:34:56"
}
```

Logs saved to `logs/agent_framework.log`.

## 🎯 Load Balancing Strategies

### Round-Robin (default)
Cycle through agents in order.

### Least-Busy
Select agent with highest success rate (completed / (completed + failed)).

### Random
Pick random available agent.

Change strategy in `.env`:

```bash
LOAD_BALANCER_STRATEGY=least_busy
```

## 🔧 Advanced Usage

### Custom Workflows

See `src/orchestrator/workflow_engine.py` for multi-step workflow examples.

### Custom Tools

Add tools to agents by extending the `process_task()` method:

```python
def process_task(self, task_input: str) -> str:
    if "search" in task_input.lower():
        return self._web_search_tool(task_input)
    # ... existing logic
```

### Database Queries

```python
from src.database import get_session, close_session
from src.database.models import TaskModel, TaskStatus

session = get_session()
completed = session.query(TaskModel).filter(
    TaskModel.status == TaskStatus.COMPLETED
).all()
close_session(session)
```

## 🐛 Troubleshooting

**Kafka connection failed on macOS:**
- Framework auto-sets `api_version=(0, 10, 1)` to skip handshake issues

**"No available agents":**
- Ensure agents are running and have heartbeated
- Check `AGENT_HEALTH_CHECK_INTERVAL` (default 30s)

**Database locked:**
- Using SQLite? Ensure only one process writes at a time
- Switch to PostgreSQL for production

**Torch/transformers slow to import:**
- Use `run_lite_agent.py` for testing without heavy models

## 📚 Next Steps

- [ ] Add more agent tools (web search, file I/O, API calls)
- [ ] Implement workflow UI
- [ ] Add Redis caching
- [ ] Deploy agents in Docker containers
- [ ] Add Prometheus metrics export
- [ ] Write unit & integration tests

---

**Need help?** Check logs in `logs/agent_framework.log` or enable debug logging:

```bash
LOG_LEVEL=DEBUG python3 run_api.py
```
