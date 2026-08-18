"""
WSGI config for YumYatra project.

It exposes the WSGI callable as a module-level variable named ``application``.
Also defines ``app = application`` for Vercel Serverless deployment.
"""

import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

# Ensure project root is in sys.path for Vercel serverless execution
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

for p in [str(BASE_DIR), str(PROJECT_DIR)]:
    if p not in sys.path:
        sys.path.append(p)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YumYatra.settings')

application = get_wsgi_application()

# Vercel entrypoint alias
app = application
