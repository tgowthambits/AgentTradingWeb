from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trading", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="control",
            field=models.CharField(
                choices=[("run", "Run"), ("pause", "Pause"), ("stop", "Stop")],
                default="run",
                help_text="Cross-process control flag read by the Celery task every iteration",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="livesession",
            name="control",
            field=models.CharField(
                choices=[("run", "Run"), ("pause", "Pause"), ("stop", "Stop")],
                default="run",
                help_text="Cross-process control flag read by the Celery task every iteration",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="backtestrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("running", "Running"),
                    ("paused", "Paused"),
                    ("stopping", "Stopping"),
                    ("stopped", "Stopped"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="livesession",
            name="status",
            field=models.CharField(
                choices=[
                    ("idle", "Idle"),
                    ("running", "Running"),
                    ("paused", "Paused"),
                    ("stopping", "Stopping"),
                    ("stopped", "Stopped"),
                    ("error", "Error"),
                ],
                default="idle",
                max_length=20,
            ),
        ),
    ]
