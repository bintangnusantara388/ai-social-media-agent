"""
Vercel Serverless Function Entrypoint
Exposes the Flask application to Vercel WSGI runtime.
"""

import os
import sys
from pathlib import Path

# Mark as running in Vercel environment
os.environ["VERCEL"] = "1"

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from admin_app import app

# Vercel entrypoint handler
app_handler = app
