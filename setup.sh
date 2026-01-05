#!/bin/bash
# Quick start script for the AI Agent Framework

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python3"

echo "🚀 AI Agent Framework - Quick Start"
echo "===================================="
echo ""

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "📦 Installing dependencies..."
$PYTHON -m pip install -q --upgrade pip 2>/dev/null || true
$PYTHON -m pip install -q -r "$PROJECT_DIR/requirements.txt" 2>/dev/null || true

echo "✅ Environment ready"
echo ""

# Start Kafka
echo "🐳 Starting Kafka..."
cd "$PROJECT_DIR"
docker compose up -d > /dev/null 2>&1
sleep 3

# Initialize database
echo "💾 Initializing database..."
$PYTHON << 'INIT_DB'
from src.database import init_db, get_session, close_session
from src.database.models import UserModel
import uuid

try:
    init_db()
    session = get_session()
    
    # Check if admin user already exists
    admin_exists = session.query(UserModel).filter(UserModel.username == 'admin').first()
    
    if not admin_exists:
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
    print("✅ Database ready (Admin API key: sk-default-admin-key)")
except Exception as e:
    print(f"❌ Database error: {e}")
INIT_DB

echo ""
echo "🎯 Services to start (open separate terminals):"
echo ""
echo "1. API Server:"
echo "   cd '$PROJECT_DIR' && source venv/bin/activate && python3 run_api.py"
echo ""
echo "2. Lite Agent:"
echo "   cd '$PROJECT_DIR' && source venv/bin/activate && python3 run_lite_agent.py"
echo ""
echo "3. Run Demo (after API + Agent are running):"
echo "   cd '$PROJECT_DIR' && source venv/bin/activate && python3 demo_tasks.py"
echo ""
echo "4. Check System Health:"
echo "   curl http://127.0.0.1:8000/health"
echo ""
echo "✨ Setup complete!"
