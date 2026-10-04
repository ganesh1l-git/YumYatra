from django.apps import AppConfig
from django.db.backends.signals import connection_created

def configure_sqlite(sender, connection, **kwargs):
    """Enable SQLite WAL mode and concurrency optimization to eliminate locking and lag."""
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode = WAL;')
        cursor.execute('PRAGMA synchronous = NORMAL;')
        cursor.execute('PRAGMA busy_timeout = 5000;')
        cursor.execute('PRAGMA cache_size = -20000;')  # ~20MB memory cache

class DeliveryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'delivery'

    def ready(self):
        connection_created.connect(configure_sqlite)

