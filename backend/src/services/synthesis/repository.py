from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.landscape import Landscape
from src.schemas.landscape import LandscapePayload


def normalize_topic(topic: str) -> str:
    return " ".join(topic.lower().split())


async def load_landscape(session: AsyncSession, topic: str) -> LandscapePayload | None:
    row = (
        await session.execute(
            select(Landscape).where(Landscape.topic == normalize_topic(topic))
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return LandscapePayload.model_validate(row.data)


async def save_landscape(session: AsyncSession, payload: LandscapePayload) -> None:
    topic = normalize_topic(payload.topic)
    row = (
        await session.execute(select(Landscape).where(Landscape.topic == topic))
    ).scalar_one_or_none()
    if row is None:
        row = Landscape(topic=topic)
        session.add(row)
    row.version = payload.version
    row.paper_count = len(payload.paper_versions)
    row.data = payload.model_dump()
    await session.commit()
