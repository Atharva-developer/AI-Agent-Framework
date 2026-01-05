#!/usr/bin/env python3
"""
Run the Lite Agent with Retry Logic and Task Dependencies.
"""

from src.agents.lite_agent_retry import run_lite_agent_with_retry

if __name__ == '__main__':
    run_lite_agent_with_retry("Lite Agent v2")
