import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Set test environment before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PAYMENT_MODE"] = "simulator"
os.environ["ADMIN_SECRET_KEY"] = "test_admin_secret_key"

from backend.database import Base, get_db
from backend.main import app
from backend.models import Fact

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingAsyncSessionLocal() as session:
        # Seed test facts
        fact1 = Fact(
            id=1,
            title="A Day Longer Than a Year",
            teaser="There is a planet where one day lasts longer than its year...",
            fact_text="A day on Venus is longer than a year on Venus.",
            explanation="Venus takes 243 Earth days to rotate once.",
            category="Space",
            source_name="NASA",
            source_url="https://science.nasa.gov/venus",
            interestingness_score=5,
            verification_status="verified",
            is_active=True
        )
        fact2 = Fact(
            id=2,
            title="Ancient Meteor Lake",
            teaser="In Maharashtra lies a crater lake created by a meteorite...",
            fact_text="Lonar Lake was formed by a 2-million-tonne meteorite crash.",
            explanation="Formed 52,000 years ago with both saline and alkaline zones.",
            category="India",
            source_name="Geological Survey of India",
            source_url="https://earthobservatory.nasa.gov",
            interestingness_score=5,
            verification_status="verified",
            is_active=True
        )
        session.add_all([fact1, fact2])
        await session.commit()

    async with TestingAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
