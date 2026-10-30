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
        # Prefer original client URI from Vercel proxy headers
        orig = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_MATCHED_PATH")
        if orig:
            environ["PATH_INFO"] = orig.split("?")[0]
        else:
            path = environ.get("PATH_INFO", "")
            if path in ("/api/index", "/api/index.py", "/api", ""):
                environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)

# Apply middleware to Flask WSGI
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# Expose WSGI app for Vercel
# Vercel looks for 'app' by default
app_handler = app
