# Intel AI Agent Framework

Small experimental framework that demonstrates a Kafka-driven micro-agent architecture with lightweight agents, an orchestrator/workflow engine, and a simple dashboard.

## Project Structure

- `src/agents/` — Agent implementations (`lite_agent.py`, `base_agents.py`).
- `src/orchestrator/` — Orchestrator and workflow engine (`manager.py`, `workflow_engine.py`).
- `src/dashboard/` — Simple terminal and web dashboards (`term_dash.py`, `web_app.py`).
- `docker-compose.yml` — Local Kafka + Zookeeper configuration used for development.
- `requirements.txt` — Python dependencies.

## Goals

- Route tasks via Kafka topics: `pending_tasks` → agents consume → agents send results to `completed_tasks`.
- Demonstrate tool usage (calculator) in agents, and how an orchestrator can run multi-step workflows.

## Prerequisites

- macOS or Linux
- Docker & Docker Compose (for Kafka)
- Python 3.11+ (recommended)

## Quick Setup (local)

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Start Kafka + Zookeeper

```bash
docker-compose up -d
```

Note: `docker-compose.yml` already creates a topic `pending_tasks` for convenience.

## Running components

- Send a test task from the Manager (producer):

```bash
python src/orchestrator/manager.py
```

- Start a lightweight agent (no heavy model required):

```bash
python src/agents/lite_agent.py
```

- Start the orchestrator workflow engine (runs a sample flow):

```bash
python src/orchestrator/workflow_engine.py
```

- Run the terminal dashboard:

```bash
python src/dashboard/term_dash.py
```

- Run the web dashboard (Flask):

```bash
python src/dashboard/web_app.py
# then open http://127.0.0.1:5000 in your browser
```

## Notes & Troubleshooting

- If Kafka connection fails on macOS, the code uses `api_version=(0, 10, 1)` in several places to avoid handshake issues with the Dockerized Kafka. This is an intentional compatibility setting.
- Optional Intel/OpenVINO packages are not required for local development. Only install them on supported Intel hardware.
- If you need persistent Kafka topics or more advanced config, edit `docker-compose.yml`.

## Contributing / Next steps

- Add unit tests for agents and orchestrator flows.
- Add dockerized agent runners for easier local testing.

---

If you want, I can also:

- Pin dependency versions in `requirements.txt` for reproducible installs.
- Create a `Makefile` or helper scripts to start all services.

Happy to continue — tell me which next step you prefer.
