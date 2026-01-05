"""
Entry point to start the REST API server.
"""

from src.api import run_api
from src.database import init_db
from src.logging import setup_logger
from config import API_HOST, API_PORT

logger = setup_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    
    logger.info("Starting REST API server...")
    run_api(host=API_HOST, port=API_PORT, reload=False)
