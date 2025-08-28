# Импорт Celery для автоматического обнаружения
from .celery import app as celery_app

__all__ = ('celery_app',)
