"""
Backend test suite for Speakly.
"""

import sys
from pathlib import Path

# Ensure the project root (containing the `backend` package) is on sys.path
# Add the backend directory (containing the `app` package) to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)
