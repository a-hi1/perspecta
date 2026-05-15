"""Initialize the database: create all tables and default user.

Usage:
    python init_db.py
"""

import asyncio
from app.db import engine, Base
from app.db.session import async_session_factory

# Import all models so Base.metadata knows about them
from app.models import (  # noqa: F401
    User,
    Document,
    DocumentChunk,
    HotTopic,
    Perspective,
    Draft,
    DraftVersion,
    StyleProfile,
    Citation,
    AgentRunLog,
    WorkflowRun,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建成功。")

    # Create default user if not exists
    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == "default_user"))
        if not result.scalar_one_or_none():
            default_user = User(
                id="default_user",
                name="默认用户",
                email="default@perspecta.local",
            )
            session.add(default_user)
            await session.commit()
            print("默认用户创建成功。")
        else:
            print("默认用户已存在。")


if __name__ == "__main__":
    asyncio.run(init_db())
