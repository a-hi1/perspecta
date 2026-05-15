"""Hot topic endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.hot_topic import HotTopic
from app.schemas.hot_topic import HotTopicResponse, HotTopicListResponse

router = APIRouter()


@router.get("/", response_model=HotTopicListResponse)
async def list_hot_topics(
    source: str | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """List discovered hot topics."""
    query = select(HotTopic).order_by(HotTopic.composite_score.desc())
    if source:
        query = query.where(HotTopic.source == source)
    if status:
        query = query.where(HotTopic.status == status)
    result = await session.execute(query)
    topics = result.scalars().all()
    return HotTopicListResponse(topics=topics, total=len(topics))


@router.get("/{topic_id}", response_model=HotTopicResponse)
async def get_hot_topic(
    topic_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific hot topic."""
    result = await session.execute(select(HotTopic).where(HotTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="话题未找到")
    return topic
