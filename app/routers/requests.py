import uuid

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from jsonschema import ValidationError, validate
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import CacheKeys, CacheTTL, delete_cached, get_cached, set_cached
from app.database import get_db
from app.models import DocumentRequest, RequestStatus, Template, User
from app.schemas import DocumentRequestCreate, DocumentRequestFromText, DocumentRequestOut
from app.security import get_current_user
from app.services.extraction import ExtractionError, extract_input_data
from app.tasks.documents import generate_document

router = APIRouter(prefix="/requests", tags=["requests"])


async def _create_document_request(
    db: AsyncSession, user: User, template: Template, input_data: dict
) -> DocumentRequest:
    request = DocumentRequest(user_id=user.id, template_id=template.id, input_data=input_data)

    db.add(request)
    await db.commit()
    await db.refresh(request)

    generate_document.delay(str(request.id))  # type: ignore[attr-defined]

    await delete_cached(CacheKeys.user_requests(str(user.id)))

    return request


@router.post("", response_model=DocumentRequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    data: DocumentRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    template = (await db.execute(select(Template).where(Template.slug == data.template_slug))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        validate(instance=data.input_data, schema=template.schema)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"input_data does not match template schema: {exc.message}",
        )

    return await _create_document_request(db, current_user, template, data.input_data)


@router.post("/from-text", response_model=DocumentRequestOut, status_code=status.HTTP_201_CREATED)
async def create_request_from_text(
    data: DocumentRequestFromText,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (await db.execute(select(Template).where(Template.slug == data.template_slug))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Template not found")

    try:
        input_data = await extract_input_data(data.text, template)
        validate(instance=input_data, schema=template.schema)
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Extracted data does not match template schema: {exc.message}",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Anthropic API rate limit exceeded, please retry shortly",
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Anthropic API error: {exc.message}",
        )
    except anthropic.APIConnectionError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the Anthropic API",
        )

    return await _create_document_request(db, current_user, template, input_data)


@router.get("", response_model=list[DocumentRequestOut])
async def get_requests(
    skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    cache_key = CacheKeys.user_requests(str(current_user.id))
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached[skip : skip + limit]

    requests = (
        (
            await db.execute(
                select(DocumentRequest)
                .where(DocumentRequest.user_id == current_user.id)
                .order_by(desc(DocumentRequest.created_at))
                .limit(50)
            )
        )
        .scalars()
        .all()
    )

    result = [DocumentRequestOut.model_validate(r).model_dump(mode="json") for r in requests]
    await set_cached(cache_key, result, CacheTTL.USER_REQUESTS)

    return result[skip : skip + limit]


@router.get("/{request_id}", response_model=DocumentRequestOut)
async def get_request(
    request_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    request = (
        await db.execute(
            select(DocumentRequest).where(DocumentRequest.id == request_id, DocumentRequest.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return request


@router.get("/{request_id}/download")
async def download_request(
    request_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    request = (
        await db.execute(
            select(DocumentRequest).where(DocumentRequest.id == request_id, DocumentRequest.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.completed:
        raise HTTPException(status_code=400, detail="Document not ready yet")

    if not request.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=request.file_path, media_type="application/pdf", filename=f"document_{request_id}.pdf")


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_request(
    request_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    request = (
        await db.execute(
            select(DocumentRequest).where(DocumentRequest.id == request_id, DocumentRequest.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")

    request.status = RequestStatus.cancelled
    await db.commit()
    await delete_cached(CacheKeys.user_requests(str(current_user.id)))
