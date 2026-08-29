from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models.entities import Carousel, CarouselSlide

async def fetch_full_carousel(db: AsyncSession, carousel_id: str):
    db.expire_all()
    stmt = (
        select(Carousel)
        .where(Carousel.id == carousel_id)
        .options(
            selectinload(Carousel.slides).selectinload(CarouselSlide.elements),
            selectinload(Carousel.exports)
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
