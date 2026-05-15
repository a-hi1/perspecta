"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import documents, workflow, drafts, topics, perspectives

api_router = APIRouter()

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["知识库"],
)
api_router.include_router(
    workflow.router,
    prefix="/workflow",
    tags=["Agent 工作流"],
)
api_router.include_router(
    drafts.router,
    prefix="/drafts",
    tags=["草稿"],
)
api_router.include_router(
    topics.router,
    prefix="/topics",
    tags=["热点话题"],
)
api_router.include_router(
    perspectives.router,
    prefix="/perspectives",
    tags=["观点"],
)
