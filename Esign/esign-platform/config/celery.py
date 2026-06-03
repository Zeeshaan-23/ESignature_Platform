# config/celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('esign')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'process-expirations-every-hour': {
        'task': 'notifications.tasks.process_expirations',
        'schedule': crontab(minute=0),  # Top of every hour
    },
    'process-reminders-every-day': {
        'task': 'notifications.tasks.process_reminders',
        'schedule': crontab(hour=0, minute=0),  # Midnight every day
    },
}