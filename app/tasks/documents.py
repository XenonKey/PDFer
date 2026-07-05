import logging
import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models import DocumentRequest, RequestStatus, Template

logger = logging.getLogger(__name__)

GENERATED_DOCS_DIR = "/app/generated_docs"
STUCK_PROCESSING_TIMEOUT_MINUTES = 30
GENERATED_DOCS_RETENTION_DAYS = 7


def generate_pdf_file(template: Template, input_data: dict) -> str:
    """Placeholder renderer: writes a plaintext stand-in instead of a real PDF.

    A real implementation would render `template.html_template` (a Jinja2 template)
    with `input_data` and convert the result to PDF, e.g. via WeasyPrint or
    wkhtmltopdf. Swapping that in only requires changing this function.
    """
    os.makedirs(GENERATED_DOCS_DIR, exist_ok=True)
    file_path = f"{GENERATED_DOCS_DIR}/{template.slug}_{datetime.now().timestamp()}.pdf"
    with open(file_path, "w") as f:
        f.write(f"Document: {template.name}\nData: {input_data}")
    return file_path


@celery_app.task(bind=True, queue="documents", max_retries=3)
def generate_document(self, request_id: str):
    with SyncSessionLocal() as db:
        request = db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id)).scalar_one_or_none()
        if not request:
            logger.warning("Request not found, skipping", extra={"request_id": request_id})
            return {"status": "error", "message": "Request not found"}

        try:
            request.status = RequestStatus.processing
            request.started_at = datetime.now(timezone.utc)
            db.commit()

            logger.info("Started processing request", extra={"request_id": request_id, "user_id": str(request.user_id)})

            template = db.get(Template, request.template_id)
            if not template:
                raise ValueError(f"Template {request.template_id} not found")

            file_path = generate_pdf_file(template, request.input_data)

            request.status = RequestStatus.completed
            request.file_path = file_path
            request.completed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info("Document generated successfully", extra={"request_id": request_id, "file_path": file_path})

            from app.tasks.notifications import send_notification

            send_notification.delay(str(request.id), str(request.user_id))  # type: ignore[attr-defined]

            return {"status": "success", "file_path": file_path}

        except Exception as exc:
            request.status = RequestStatus.failed
            request.error_message = str(exc)
            db.commit()

            logger.error(
                "Failed to generate document", extra={"request_id": request_id, "error": str(exc)}, exc_info=True
            )
            raise self.retry(exc=exc, countdown=60)


@celery_app.task(queue="documents")
def reap_stuck_requests():
    """Fail requests stuck in `processing` for too long (e.g. a worker died mid-job)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_PROCESSING_TIMEOUT_MINUTES)

    with SyncSessionLocal() as db:
        stuck = (
            db.execute(
                select(DocumentRequest).where(
                    DocumentRequest.status == RequestStatus.processing,
                    DocumentRequest.started_at < cutoff,
                )
            )
            .scalars()
            .all()
        )

        for request in stuck:
            request.status = RequestStatus.failed
            request.error_message = f"Timed out: did not finish within {STUCK_PROCESSING_TIMEOUT_MINUTES} minutes"

        db.commit()

    if stuck:
        logger.warning("Reaped stuck requests", extra={"count": len(stuck)})

    return {"reaped": len(stuck)}


@celery_app.task(queue="documents")
def cleanup_old_generated_docs():
    """Delete generated documents older than the retention window.

    Local filesystem storage isn't durable or shared across instances; in a real
    deployment `generated_docs` would live in object storage (e.g. S3) instead.
    """
    cutoff = time.time() - GENERATED_DOCS_RETENTION_DAYS * 86400
    removed = 0

    if os.path.isdir(GENERATED_DOCS_DIR):
        for name in os.listdir(GENERATED_DOCS_DIR):
            path = os.path.join(GENERATED_DOCS_DIR, name)
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1

    if removed:
        logger.info("Cleaned up old generated documents", extra={"removed": removed})

    return {"removed": removed}
