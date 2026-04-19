from django.core.management.base import BaseCommand
import subprocess

class Command(BaseCommand):
    help = "Run Django server + Celery worker"

    def handle(self, *args, **kwargs):
        celery = subprocess.Popen([
            "uv", "run", "celery", "-A", "web_platform",
            "worker", "--loglevel=info", "--pool=gevent"
        ])

        django = subprocess.Popen([
            "uv", "run", "python", "manage.py", "runserver"
        ])

        try:
            celery.wait()
            django.wait()
        except KeyboardInterrupt:
            celery.terminate()
            django.terminate()