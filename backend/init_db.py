"""Initialize the database: create all tables.

Usage:
    python init_db.py
"""

import asyncio
from app.db import engine, Base

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
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
