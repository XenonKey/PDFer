import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import DocumentRequest


async def get_extraction_job_status(job_id: str) -> str:

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return f"'{job_id}' doesn't look like a valid job id (expected a UUID)."

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == job_uuid))
        job = result.scalar_one_or_none()

    if job is None:
        return f"No job found with id {job_id}."

    answer = f"Status of job {job_id}: {job.status.value}. Created: {job.created_at.isoformat()}."
    if job.error_message:
        answer += f" Error: {job.error_message}"

    return answer
