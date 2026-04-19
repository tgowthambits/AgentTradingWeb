import os

# gevent monkey-patches asyncio which makes Django's "async-unsafe" guard fire
# inside Celery's post-task hook (close_database). Mark the worker as sync-safe
# so the ORM can run freely.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_platform.settings")

from celery import Celery  # noqa: E402

app = Celery("web_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
