#!/usr/bin/env python3
"""
Run the Task Scheduler Service.
"""

from src.orchestrator.scheduler import run_scheduler

if __name__ == '__main__':
    run_scheduler()
