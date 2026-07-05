from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.observability.logging_config import setup_logging

setup_logging()

celery_app = Celery("pdfer", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        "app.tasks.documents.*": {"queue": "documents"},
        "app.tasks.notifications.*": {"queue": "notifications"},
    },
    beat_schedule={
        "reap-stuck-requests": {
            "task": "app.tasks.documents.reap_stuck_requests",
            "schedule": crontab(minute="*/15"),
        },
        "cleanup-old-generated-docs": {
            "task": "app.tasks.documents.cleanup_old_generated_docs",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks.documents", "app.tasks.notifications"])
