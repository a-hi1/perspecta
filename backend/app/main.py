"""FastAPI application entry point."""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api.v1.router import api_router
from app.observability.logger import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logging()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="个人经验放大器 - AI 驱动的观点发现与内容策划系统",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS - 开发模式下完全放宽
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理的异常: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"服务器内部错误: {exc}"},
        )

    # Routes
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Debug: List all routes
    @app.get("/debug/routes")
    async def list_routes():
        route_list = []
        for route in app.routes:
            if hasattr(route, "path"):
                route_list.append(route.path)
        return {"routes": route_list}

    @app.get("/health")
    async def health():
        return {
            "status": "正常",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
        }

    return app


app = create_app()
