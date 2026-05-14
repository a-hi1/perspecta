"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import documents, workflow, drafts, topics, perspectives

api_router = APIRouter()

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Knowledge Base"],
)
api_router.include_router(
    workflow.router,
    prefix="/workflow",
    tags=["Agent Workflow"],
)
api_router.include_router(
    drafts.router,
    prefix="/drafts",
    tags=["Drafts"],
)
api_router.include_router(
    topics.router,
    prefix="/topics",
    tags=["Hot Topics"],
)
api_router.include_router(
    perspectives.router,
    prefix="/perspectives",
    tags=["Perspectives"],
)
