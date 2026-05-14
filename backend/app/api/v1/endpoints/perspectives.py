"""Perspective endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.perspective import Perspective
from app.schemas.perspective import PerspectiveResponse, PerspectiveListResponse

router = APIRouter()


@router.get("/", response_model=PerspectiveListResponse)
async def list_perspectives(
    perspective_type: str | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """List discovered perspectives."""
    query = select(Perspective).order_by(Perspective.confidence.desc())
    if perspective_type:
        query = query.where(Perspective.perspective_type == perspective_type)
    if status:
        query = query.where(Perspective.status == status)
    result = await session.execute(query)
    perspectives = result.scalars().all()
    return PerspectiveListResponse(perspectives=perspectives, total=len(perspectives))


@router.get("/{perspective_id}", response_model=PerspectiveResponse)
async def get_perspective(
    perspective_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific perspective with source references."""
    result = await session.execute(
        select(Perspective).where(Perspective.id == perspective_id)
    )
    perspective = result.scalar_one_or_none()
    if not perspective:
        raise HTTPException(status_code=404, detail="Perspective not found")
    return perspective


@router.put("/{perspective_id}/feedback")
async def update_perspective_feedback(
    perspective_id: str,
    feedback: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Update user feedback on a perspective."""
    result = await session.execute(
        select(Perspective).where(Perspective.id == perspective_id)
    )
    perspective = result.scalar_one_or_none()
    if not perspective:
        raise HTTPException(status_code=404, detail="Perspective not found")

    perspective.user_feedback = feedback
    await session.commit()
    return {"status": "updated", "perspective_id": perspective_id}
