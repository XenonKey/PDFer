from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import CacheKeys, CacheTTL, get_cached, set_cached
from app.database import get_db
from app.models import Template
from app.schemas import TemplateListItem, TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateListItem])
async def get_templates(db: AsyncSession = Depends(get_db)):

    cache_key = CacheKeys.templates_list()
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    templates = (await db.execute(select(Template))).scalars().all()

    result = [TemplateListItem.model_validate(t).model_dump() for t in templates]
    await set_cached(cache_key, result, CacheTTL.TEMPLATES)

    return result


@router.get("/{slug}", response_model=TemplateOut)
async def get_template(slug: str, db: AsyncSession = Depends(get_db)):

    cache_key = CacheKeys.template(slug)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    template = (await db.execute(select(Template).where(Template.slug == slug))).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    result = TemplateOut.model_validate(template).model_dump()
    await set_cached(cache_key, result, CacheTTL.TEMPLATES)

    return result
