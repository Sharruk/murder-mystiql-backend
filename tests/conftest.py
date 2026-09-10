"""
Pytest configuration and fixtures.
Provides an async in-memory SQLite test database with schema mapping,
pre-seeded participants and levels, and an HTTP test client.
"""

import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects import sqlite

from app.db.models import Base, Level, Participant
from app.db.session import get_db, get_investigator_pool
from app.main import app

# Create in-memory SQLite async engine with schema translation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    execution_options={"schema_translate_map": {"game": None, "investigation": None}},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create fresh tables, seed data, and yield session per test."""
    async with test_engine.begin() as conn:
        # SQLite compatibility: map JSONB to JSON
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        # Seed test participants
        p1 = Participant(
            username="DETECTIVE-01",
            display_name="Sherlock Holmes",
            seat_no="Lab-01",
        )
        p2 = Participant(
            username="DETECTIVE-02",
            display_name="John Watson",
            seat_no="Lab-02",
        )
        session.add_all([p1, p2])

        # Seed test levels
        lvl1 = Level(
            order_no=1,
            title="The Crime Scene Inspection",
            story_context="A body was found in the study.",
            question_text="What initials were on the pen?",
            correct_answer="A.V.",
            hint_text="Check the crime scene log.",
            hint_penalty_seconds=120,
            unlocks_tables=["crime_scene_log"],
        )
        lvl2 = Level(
            order_no=2,
            title="Unmasking the Initials",
            story_context="The initials lead to a suspect.",
            question_text="Who has initials A.V.?",
            correct_answer="Arthur Vance",
            hint_text="Check suspects table.",
            hint_penalty_seconds=180,
            unlocks_tables=["crime_scene_log", "suspects"],
        )
        session.add_all([lvl1, lvl2])
        await session.commit()

        yield session

        await session.close()


class MockInvestigatorPool:
    """Mock asyncpg pool for testing participant query execution flow."""
    def __init__(self):
        self.sample_rows = [
            {"item": "Vintage Fountain Pen", "location": "Desk Corner", "notes": "Engraved with initials A.V."}
        ]

    def acquire(self):
        return MockPoolConnectionContext(self.sample_rows)


class MockPoolConnectionContext:
    def __init__(self, sample_rows):
        self.sample_rows = sample_rows

    async def __aenter__(self):
        return MockConnection(self.sample_rows)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockConnection:
    def __init__(self, sample_rows):
        self.sample_rows = sample_rows

    def transaction(self, readonly=True):
        return MockTransactionContext()

    async def execute(self, query):
        return "OK"

    async def prepare(self, query):
        return MockPreparedStatement(self.sample_rows)


class MockTransactionContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockPreparedStatement:
    def __init__(self, sample_rows):
        self.sample_rows = sample_rows

    def get_attributes(self):
        class Attr:
            def __init__(self, name):
                self.name = name
        if self.sample_rows:
            return [Attr(k) for k in self.sample_rows[0].keys()]
        return []

    async def fetch(self):
        return self.sample_rows


mock_pool = MockInvestigatorPool()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide AsyncClient with DB and pool overrides."""
    async def override_get_db():
        yield test_db

    def override_get_investigator_pool():
        return mock_pool

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_investigator_pool] = override_get_investigator_pool

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
