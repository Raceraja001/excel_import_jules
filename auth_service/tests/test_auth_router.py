import pytest
from httpx import AsyncClient
from fastapi import status
import uuid

from app.config import settings
from app.schemas import UserCreate #, Token
from app.models import User as UserModel # SQLAlchemy model
from app.crud import user as user_crud # To verify user creation
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session # For direct DB interaction if needed in test setup
from app.dependencies import get_current_active_user # To potentially mock or test

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Test User Registration ---
async def test_register_new_user(
    async_client: AsyncClient, test_tenant_data: dict, db: AsyncSession # db fixture from conftest
):
    # Create a tenant first, as UserCreate schema might expect tenant_id
    tenant_res = await async_client.post(
        f"{settings.API_V1_STR}/tenants/",
        json=test_tenant_data,
        # Headers would be needed if tenant creation is protected, assuming superuser for now
        # For this test, let's assume tenant creation is open or handled by a fixture that provides headers
        # This requires a superuser to be logged in to create a tenant.
        # We need a superuser fixture that logs in and provides headers.
        # For now, this test might fail if tenant creation is protected without appropriate headers.
        # Let's assume for this specific test, we pre-create the tenant directly or use a fixture.
    )
    # A better approach: Create tenant directly via CRUD for test setup if router is protected
    from app.crud.tenant_crud import create_tenant as crud_create_tenant
    from app.schemas.tenant_schema import TenantCreate as SchemaTenantCreate
    created_tenant = await crud_create_tenant(db, SchemaTenantCreate(name="TenantForUserRegTest"))

    user_data = {
        "email": "newuser@example.com",
        "password": "SecurePassword123",
        "full_name": "New Registered User",
        "tenant_id": str(created_tenant.id) # Use the ID of the created tenant
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    created_user_json = response.json()
    assert created_user_json["email"] == user_data["email"]
    assert created_user_json["full_name"] == user_data["full_name"]
    assert "id" in created_user_json
    assert "hashed_password" not in created_user_json # Ensure password is not returned

    # Verify user in DB
    db_user = await user_crud.get_user_by_email(db, email=user_data["email"])
    assert db_user is not None
    assert db_user.email == user_data["email"]

async def test_register_existing_user_email(async_client: AsyncClient, test_user_data: dict, test_user: UserModel):
    # test_user fixture already creates a user with test_user_data["email"]
    response = await async_client.post(f"{settings.API_V1_STR}/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]


# --- Test User Login ---
async def test_login_for_access_token(async_client: AsyncClient, test_user: UserModel, test_user_data: dict):
    login_data = {
        "username": test_user_data["email"], # form_data uses 'username'
        "password": test_user_data["password"]
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

async def test_login_incorrect_password(async_client: AsyncClient, test_user: UserModel, test_user_data: dict):
    login_data = {
        "username": test_user_data["email"],
        "password": "WrongPassword"
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]

async def test_login_inactive_user(async_client: AsyncClient, test_user: UserModel, test_user_data: dict, db: AsyncSession):
    # Deactivate user
    await user_crud.deactivate_user(db, user=test_user)

    login_data = {"username": test_user_data["email"], "password": test_user_data["password"]}
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Inactive user" in response.json()["detail"]

    # Reactivate for other tests if db session is not fully isolated per test
    await user_crud.activate_user(db, user=test_user)


# --- Test Token Refresh ---
async def test_refresh_access_token(async_client: AsyncClient, test_user: UserModel, test_user_data: dict):
    # 1. Login to get initial tokens
    login_data = {"username": test_user_data["email"], "password": test_user_data["password"]}
    login_response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    initial_tokens = login_response.json()
    initial_access_token = initial_tokens["access_token"]
    refresh_token = initial_tokens["refresh_token"]

    # 2. Use refresh token to get a new access token
    refresh_headers = {"Authorization": f"Bearer {refresh_token}"}
    refresh_response = await async_client.post(f"{settings.API_V1_STR}/auth/refresh", headers=refresh_headers)

    assert refresh_response.status_code == status.HTTP_200_OK
    new_tokens = refresh_response.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != initial_access_token # New access token should be different
    # Depending on implementation, refresh token might also be new or the same
    # assert "refresh_token" in new_tokens # And potentially check if it's new/same

async def test_refresh_with_invalid_refresh_token(async_client: AsyncClient):
    invalid_refresh_token = "this.is.an.invalid.token"
    refresh_headers = {"Authorization": f"Bearer {invalid_refresh_token}"}
    response = await async_client.post(f"{settings.API_V1_STR}/auth/refresh", headers=refresh_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED # Or 422 if token format is wrong for AuthJWT
    # AuthJWT might return 422 for "Not enough segments" or "Invalid header padding"
    # If it's a valid format but expired/unknown, it would be 401
    # For this test, a clearly invalid format might trigger a different error before signature check.
    # Let's assume AuthJWT handles it and gives 401 or 422.
    # A common response for invalid token by AuthJWT is 422 "Signature verification failed" or similar.
    # If the token is just not found or subject is invalid, it might be 401.
    # Let's expect 401 as per current setup that might not validate structure before signature.

# --- Test Get Current User (/me) ---
async def test_read_users_me(async_client: AsyncClient, authenticated_headers: dict, test_user: UserModel):
    response = await async_client.get(f"{settings.API_V1_STR}/auth/me", headers=authenticated_headers)
    assert response.status_code == status.HTTP_200_OK
    user_details = response.json()
    assert user_details["email"] == test_user.email
    assert user_details["id"] == str(test_user.id)
    assert "hashed_password" not in user_details

async def test_read_users_me_unauthenticated(async_client: AsyncClient):
    response = await async_client.get(f"{settings.API_V1_STR}/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED # AuthJWT default
    assert "Not authenticated" in response.json()["detail"] # or "Missing Authorization Header" etc.

# More tests can be added:
# - Test registration with missing fields (FastAPI validation should catch this - 422)
# - Test registration with invalid email format (FastAPI/Pydantic validation - 422)
# - Test login with missing form fields (FastAPI validation - 422)
# - Test refreshing with an access token instead of a refresh token
# - Test accessing /me with an expired access token
# - Test tenant creation during registration if that logic is added.
# - Test behavior when tenant_id provided at registration does not exist.
# (already partially covered by creating tenant directly in the registration test for now)

async def test_register_user_with_nonexistent_tenant(async_client: AsyncClient):
    non_existent_tenant_id = str(uuid.uuid4())
    user_data = {
        "email": "anotheruser@example.com",
        "password": "SecurePassword123",
        "full_name": "Another User",
        "tenant_id": non_existent_tenant_id
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND # As per current router logic
    assert f"Tenant with id {non_existent_tenant_id} not found" in response.json()["detail"]
