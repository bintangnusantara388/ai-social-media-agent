"""
Vercel Serverless Function Entrypoint
Exposes the Flask application to Vercel WSGI runtime with automatic PATH_INFO normalization.
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

class VercelPathMiddleware:
    """Normalizes PATH_INFO for Vercel serverless rewrites."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Prefer HTTP_X_FORWARDED_URI (client original URI) if present and valid
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI")
        if forwarded_uri and forwarded_uri not in ("/api/index", "/api/index.py"):
            environ["PATH_INFO"] = forwarded_uri.split("?")[0]
        else:
            # 2. If PATH_INFO is the Vercel internal function path, normalize to root /
            path = environ.get("PATH_INFO", "")
            if path in ("/api/index", "/api/index.py", "/api", ""):
                environ["PATH_INFO"] = "/"
            elif path.startswith("/api/index/"):
                environ["PATH_INFO"] = path[len("/api/index"):]

        return self.wsgi_app(environ, start_response)

# Apply middleware to Flask WSGI
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# Expose WSGI app for Vercel
# Vercel looks for 'app' by default
app_handler = app
