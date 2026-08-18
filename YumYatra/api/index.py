import os
import sys
from pathlib import Path

# Add project root and inner folders to Python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
INNER_APP_DIR = PROJECT_DIR / 'YumYatra'

for path in [str(PROJECT_DIR), str(INNER_APP_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YumYatra.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application

# Auto-migrate SQLite in /tmp on serverless cold start if needed
if not os.getenv('DATABASE_URL'):
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Serverless migration note: {e}")
