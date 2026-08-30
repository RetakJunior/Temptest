#!/usr/bin/env python3
"""
Entry point for CPU-Z Hardware Monitor.
"""
import sys
import os

# Ensure package path is resolved properly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from monitor.ui_main import run_app

if __name__ == "__main__":
    run_app()
