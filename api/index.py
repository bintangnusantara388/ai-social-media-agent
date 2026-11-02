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
from werkzeug.middleware.proxy_fix import ProxyFix

# Apply ProxyFix for correct protocol and host headers behind Vercel reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


class VercelPathMiddleware:
    """Normalizes PATH_INFO for Vercel serverless rewrites and routes."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Check HTTP_X_FORWARDED_URI or HTTP_X_MATCHED_PATH if present
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_MATCHED_PATH")
        if forwarded_uri and forwarded_uri not in ("/api/index", "/api/index.py", "/api", "/api/"):
            environ["PATH_INFO"] = forwarded_uri.split("?")[0]
        else:
            # 2. Normalize internal Vercel function paths to root /
            path = environ.get("PATH_INFO", "")
            if path in ("/api/index", "/api/index.py", "/api", "/api/", "", "//"):
                environ["PATH_INFO"] = "/"
            elif path.startswith("/api/index/"):
                environ["PATH_INFO"] = "/" + path[len("/api/index/"):].lstrip("/")

        return self.wsgi_app(environ, start_response)


# Apply normalization middleware
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# Expose WSGI app for Vercel (support app, handler, and app_handler)
app_handler = app
handler = app
