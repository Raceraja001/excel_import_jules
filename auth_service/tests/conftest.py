import asyncio
import pytest
from typing import AsyncGenerator, Generator, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Assuming your main FastAPI app instance is in app.main
from app.main import app
from app.config import settings # To override settings if needed
from app.database import Base, get_db_session as app_get_db_session
from app.models import User, Tenant # For creating test data
from app.schemas import UserCreate, TenantCreate # For creating test data
from app.security import get_password_hash

# --- Test Database Setup ---
# Use a different database for testing if possible, e.g., by setting TEST_DATABASE_URL environment variable
# For simplicity, this example might use the same DB schema but with transactions for isolation.
# A more robust setup would use a dedicated test DB.
TEST_DATABASE_URL = settings.DATABASE_URL + "_test" # Example: append _test
# Fallback if you don't want a separate DB file for SQLite, or just use the dev one and rely on transactions.
# TEST_DATABASE_URL = settings.DATABASE_URL

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False) # Set echo=True for SQL debugging
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Override FastAPI's get_db_session dependency for tests.
    Uses a transaction that's rolled back after each test.
    """
    async with TestingSessionLocal() as session:
        async with session.begin(): # Start a transaction
            try:
                yield session
            finally:
                await session.rollback() # Rollback changes after test


# Apply the override for the whole test suite
app.dependency_overrides[app_get_db_session] = override_get_db_session

@pytest.fixture(scope="session")
def event_loop(request: Any) -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Create test database tables before tests run and drop them after.
    'autouse=True' ensures this runs automatically for the session.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an HTTPX AsyncClient for making requests to the test app.
    """
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

# --- Test Data Fixtures ---

@pytest.fixture
def test_tenant_data() -> dict:
    return {"name": "Test Tenant Inc."}

@pytest.fixture
async def test_tenant(db: AsyncSession = Depends(override_get_db_session), test_tenant_data: dict) -> Tenant:
    tenant = Tenant(**test_tenant_data)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

@pytest.fixture
def test_user_password() -> str:
    return "TestPassword123!"

@pytest.fixture
def test_user_data(test_tenant: Tenant, test_user_password) -> dict:
    return {
        "email": "testuser@example.com",
        "password": test_user_password,
        "full_name": "Test User",
        "tenant_id": test_tenant.id,
        "is_active": True,
        "is_superuser": False,
    }

@pytest.fixture
async def test_user(db: AsyncSession = Depends(override_get_db_session), test_user_data: dict) -> User:
    user_create = UserCreate(**test_user_data)
    user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        tenant_id=user_create.tenant_id,
        is_active=user_create.is_active,
        is_superuser=user_create.is_superuser,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.fixture
def test_superuser_data(test_user_password) -> dict:
    return {
        "email": "superadmin@example.com",
        "password": test_user_password,
        "full_name": "Super Admin",
        "tenant_id": None, # Superuser might not belong to a tenant
        "is_active": True,
        "is_superuser": True,
    }

@pytest.fixture
async def test_superuser(db: AsyncSession = Depends(override_get_db_session), test_superuser_data: dict) -> User:
    user_create = UserCreate(**test_superuser_data) # Use UserCreate for password field
    user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password), # Hash the password
        full_name=user_create.full_name,
        tenant_id=user_create.tenant_id,
        is_active=user_create.is_active,
        is_superuser=user_create.is_superuser,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# Fixture to get authenticated headers for a user
@pytest.fixture
async def authenticated_headers(async_client: AsyncClient, test_user_data: dict) -> dict:
    # Create user first if not using a pre-existing one from another fixture
    # For simplicity, assume test_user fixture has run or we register/login here.
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"] # Use the raw password
    }
    # Ensure user exists for login - this depends on test_user fixture being called or user created
    # If test_user fixture is not auto-used, you might need to create the user here explicitly
    # await async_client.post(f"{settings.API_V1_STR}/auth/register", json=test_user_data) # If registration is pathway

    res = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    if res.status_code != 200:
        print("Login failed in authenticated_headers fixture:", res.json()) # Debugging
        raise Exception("Login failed in authenticated_headers fixture")

    tokens = res.json()
    access_token = tokens["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
async def superuser_authenticated_headers(async_client: AsyncClient, test_superuser_data: dict, test_superuser: User) -> dict:
    # test_superuser fixture ensures the superuser exists in DB
    login_data = {
        "username": test_superuser_data["email"],
        "password": test_superuser_data["password"] # Use the raw password
    }
    res = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    if res.status_code != 200:
        print("Superuser login failed in fixture:", res.json()) # Debugging
        raise Exception("Superuser login failed in authenticated_headers fixture")

    tokens = res.json()
    access_token = tokens["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
