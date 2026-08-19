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

# Auto-migrate and auto-seed on serverless cold start if database is empty
try:
    from django.core.management import call_command
    from delivery.models import Restaurant
    call_command('migrate', interactive=False)
    if Restaurant.objects.count() == 0:
        call_command('loaddata', 'initial_data')
except Exception as e:
    print(f"Cold-start auto-setup note: {e}")
