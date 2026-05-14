"""Draft management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.draft import Draft, DraftVersion
from app.schemas.draft import DraftResponse, DraftUpdateRequest, DraftListResponse

router = APIRouter()


@router.get("/", response_model=DraftListResponse)
async def list_drafts(
    status: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """List all drafts, optionally filtered by status."""
    query = select(Draft).order_by(Draft.created_at.desc())
    if status:
        query = query.where(Draft.status == status)
    result = await session.execute(query)
    drafts = result.scalars().all()
    return DraftListResponse(drafts=drafts, total=len(drafts))


@router.get("/{draft_id}", response_model=DraftResponse)
async def get_draft(
    draft_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific draft."""
    result = await session.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.put("/{draft_id}", response_model=DraftResponse)
async def update_draft(
    draft_id: str,
    request: DraftUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Update a draft's content (human editing)."""
    result = await session.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Save version history
    version = DraftVersion(
        draft_id=draft_id,
        version_number=draft.version,
        content=draft.content,
        change_summary=request.change_summary,
        changed_by="human",
    )
    session.add(version)

    # Update draft
    draft.content = request.content
    draft.version += 1

    await session.commit()
    return draft


@router.get("/{draft_id}/versions")
async def get_draft_versions(
    draft_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get version history for a draft."""
    result = await session.execute(
        select(DraftVersion)
        .where(DraftVersion.draft_id == draft_id)
        .order_by(DraftVersion.version_number)
    )
    versions = result.scalars().all()
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "content": v.content,
            "change_summary": v.change_summary,
            "changed_by": v.changed_by,
            "created_at": v.created_at,
        }
        for v in versions
    ]
