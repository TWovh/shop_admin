import os
from celery import Celery

# Устанавливаем переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopadmin.settings')

app = Celery('shopadmin')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'cleanup-old-payments': {
        'task': 'shop.tasks.cleanup_old_payments_task',
        'schedule': 3600.0,  # каждый час
    },
    'cleanup-old-orders': {
        'task': 'shop.tasks.cleanup_old_orders_task',
        'schedule': 86400.0,  # каждый день
    },
}

#retry 
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'Europe/Kiev'
app.conf.enable_utc = True

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 