"""
Configuration package for PanierFacile.

This package contains Django configuration files:
- settings.py: Django settings
- urls.py: URL routing
- celery.py: Celery configuration for async tasks
- wsgi.py: WSGI application
- asgi.py: ASGI application
"""

# Import Celery pour que les tâches soient auto-découvertes
from .celery import app as celery_app

__all__ = ('celery_app',)
