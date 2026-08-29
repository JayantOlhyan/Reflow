from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models.entities import Clip

async def fetch_full_clip(db: AsyncSession, clip_id: str):
    db.expire_all()
    stmt = (
        select(Clip)
        .where(Clip.id == clip_id)
        .options(
            selectinload(Clip.variants)
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def fetch_content_clips(db: AsyncSession, content_id: str):
    db.expire_all()
    stmt = (
        select(Clip)
        .where(Clip.content_id == content_id)
        .options(
            selectinload(Clip.variants)
        )
        .order_by(Clip.score.desc(), Clip.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
