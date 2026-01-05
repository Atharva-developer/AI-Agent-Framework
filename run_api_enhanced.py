#!/usr/bin/env python3
"""
Run the Enhanced API Server with advanced features.
"""

from src.api import run_api

if __name__ == '__main__':
    run_api(reload=False)
