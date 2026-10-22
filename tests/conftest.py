import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.cache import get_redis
from app.core.database import Base, get_db
from app.core.security import SecurityService
from app.main import app
from app.models.user import User

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Create test Redis client"""
    redis = Redis.from_url("redis://localhost:6379/1", decode_responses=True)
    yield redis
    await redis.flushdb()
    await redis.close()


@pytest.fixture(scope="function")
async def client(
    db_session: AsyncSession, redis_client: Redis
) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user"""
    security = SecurityService()
    user = User(
        email="test@example.com",
        hashed_password=security.get_password_hash("Test123!"),
        first_name="Test",
        last_name="User",
        role="applicant",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user"""
    security = SecurityService()
    admin = User(
        email="admin@example.com",
        hashed_password=security.get_password_hash("Admin123!"),
        first_name="Admin",
        last_name="User",
        role="administrator",
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def auth_headers(test_user: User) -> dict:
    """Get authentication headers"""
    security = SecurityService()
    token = security.create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}
