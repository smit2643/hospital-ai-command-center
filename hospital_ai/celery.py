import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hospital_ai.settings")

app = Celery("hospital_ai")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
