import os
import sys
from pathlib import Path

# Add project root and inner folders to Python path
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
PROJECT_DIR = REPO_ROOT / 'YumYatra'
INNER_APP_DIR = PROJECT_DIR / 'YumYatra'

for path in [str(PROJECT_DIR), str(INNER_APP_DIR), str(REPO_ROOT)]:
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YumYatra.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
