from datetime import datetime, timezone

from app.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models import Notification, NotificationStatus, NotificationType


@celery_app.task(bind=True, queue="notifications", max_retries=3)
def send_notification(self, request_id: str, user_id: str):
    """Placeholder channel: prints instead of sending a real email/webhook.

    A real implementation would plug in an email provider or the existing
    `NotificationType.webhook` path here; the `Notification` row it writes
    already models both.
    """
    with SyncSessionLocal() as db:
        notification = Notification(
            user_id=user_id,
            document_request_id=request_id,
            type=NotificationType.email,
            status=NotificationStatus.pending,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        try:
            print(f"[EMAIL] Document ready for user {user_id}, request {request_id}")
            notification.status = NotificationStatus.sent
            notification.sent_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as exc:
            notification.status = NotificationStatus.failed
            db.commit()
            raise self.retry(exc=exc, countdown=30)
