import pytest
from httpx import AsyncClient
from fastapi import status
import uuid

from app.config import settings
from app.schemas import UserCreate, UserUpdate
from app.models import User as UserModel, Tenant as TenantModel # SQLAlchemy models
from sqlalchemy.ext.asyncio import AsyncSession

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Test User Creation (Admin Endpoint) ---
# This endpoint (/users/) is distinct from /auth/register
# Assumed to be protected, e.g., by superuser_authenticated_headers

async def test_create_new_user_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel, # Fixture to ensure tenant exists
    db: AsyncSession # For verification
):
    new_user_email = "admincreated@example.com"
    user_data_in = {
        "email": new_user_email,
        "password": "AdminPassword123",
        "full_name": "Admin Created User",
        "tenant_id": str(test_tenant.id),
        "is_active": True,
        "is_superuser": False # Superuser creating a regular user
    }
    response = await async_client.post(
        f"{settings.API_V1_STR}/users/",
        json=user_data_in,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_user = response.json()
    assert created_user["email"] == new_user_email
    assert "hashed_password" not in created_user

    # Verify in DB
    from app.crud import user as user_crud
    db_user = await user_crud.get_user_by_email(db, email=new_user_email)
    assert db_user is not None
    assert db_user.full_name == user_data_in["full_name"]

async def test_create_user_existing_email_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_user: UserModel # Existing user
):
    user_data_in = { # Attempt to create user with same email as test_user
        "email": test_user.email,
        "password": "anotherPassword123",
        "full_name": "Duplicate User",
        "tenant_id": str(test_user.tenant_id) if test_user.tenant_id else None,
    }
    response = await async_client.post(
        f"{settings.API_V1_STR}/users/",
        json=user_data_in,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"User with email '{test_user.email}' already exists" in response.json()["detail"]

# --- Test List Users ---
async def test_read_users_list_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_user: UserModel, # Ensure at least one user exists
    test_superuser: UserModel # Ensure superuser also exists
):
    response = await async_client.get(f"{settings.API_V1_STR}/users/", headers=superuser_authenticated_headers)
    assert response.status_code == status.HTTP_200_OK
    users_list = response.json()
    assert isinstance(users_list, list)
    assert len(users_list) >= 2 # At least test_user and test_superuser

    emails_in_response = [u["email"] for u in users_list]
    assert test_user.email in emails_in_response
    assert test_superuser.email in emails_in_response

async def test_read_users_list_by_regular_user_forbidden(
    async_client: AsyncClient,
    authenticated_headers: dict # Regular user's headers
):
    response = await async_client.get(f"{settings.API_V1_STR}/users/", headers=authenticated_headers)
    # Current user_router.py protects GET /users/ with get_current_active_superuser
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "The user doesn't have enough privileges" in response.json()["detail"]


# --- Test Get Specific User ---
async def test_read_user_by_id_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_user: UserModel
):
    response = await async_client.get(
        f"{settings.API_V1_STR}/users/{test_user.id}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    user_details = response.json()
    assert user_details["email"] == test_user.email
    assert user_details["id"] == str(test_user.id)

async def test_read_own_user_details_by_regular_user(
    async_client: AsyncClient,
    authenticated_headers: dict,
    test_user: UserModel # The user whose headers these are
):
    response = await async_client.get(
        f"{settings.API_V1_STR}/users/{test_user.id}",
        headers=authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    user_details = response.json()
    assert user_details["email"] == test_user.email

async def test_read_other_user_details_by_regular_user_forbidden(
    async_client: AsyncClient,
    authenticated_headers: dict, # test_user's headers
    test_superuser: UserModel # Trying to access superuser's details
):
    response = await async_client.get(
        f"{settings.API_V1_STR}/users/{test_superuser.id}",
        headers=authenticated_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Not enough permissions" in response.json()["detail"]

async def test_read_nonexistent_user(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict
):
    non_existent_uuid = uuid.uuid4()
    response = await async_client.get(
        f"{settings.API_V1_STR}/users/{non_existent_uuid}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "User not found" in response.json()["detail"]


# --- Test Update User ---
async def test_update_user_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_user: UserModel, # User to be updated
    db: AsyncSession
):
    update_data = {"full_name": "Updated Test User Name", "is_active": False}
    response = await async_client.put(
        f"{settings.API_V1_STR}/users/{test_user.id}",
        json=update_data,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    updated_user_json = response.json()
    assert updated_user_json["full_name"] == update_data["full_name"]
    assert updated_user_json["is_active"] == update_data["is_active"]

    await db.refresh(test_user) # Refresh from DB
    assert test_user.full_name == update_data["full_name"]
    assert test_user.is_active == update_data["is_active"]

async def test_update_own_user_details_by_regular_user(
    async_client: AsyncClient,
    authenticated_headers: dict,
    test_user: UserModel, # User performing update and being updated
    db: AsyncSession
):
    update_data = {"full_name": "Self Updated Name"}
    response = await async_client.put(
        f"{settings.API_V1_STR}/users/{test_user.id}",
        json=update_data,
        headers=authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    updated_user_json = response.json()
    assert updated_user_json["full_name"] == update_data["full_name"]

    await db.refresh(test_user)
    assert test_user.full_name == update_data["full_name"]

async def test_update_user_change_email_to_existing_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_user: UserModel,
    test_superuser: UserModel, # We'll try to change test_user's email to test_superuser's email
    db: AsyncSession
):
    update_data = {"email": test_superuser.email}
    response = await async_client.put(
        f"{settings.API_V1_STR}/users/{test_user.id}",
        json=update_data,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Email '{test_superuser.email}' is already registered" in response.json()["detail"]


# --- Test Delete User ---
async def test_delete_user_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_user: UserModel, # User to be deleted
    db: AsyncSession
):
    user_id_to_delete = test_user.id
    response = await async_client.delete(
        f"{settings.API_V1_STR}/users/{user_id_to_delete}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    deleted_user_json = response.json()
    assert deleted_user_json["id"] == str(user_id_to_delete)

    from app.crud import user as user_crud
    db_user = await user_crud.get_user(db, user_id=user_id_to_delete)
    assert db_user is None # User should be deleted

async def test_delete_user_by_regular_user_forbidden(
    async_client: AsyncClient,
    authenticated_headers: dict,
    test_superuser: UserModel # Trying to delete another user
):
    response = await async_client.delete(
        f"{settings.API_V1_STR}/users/{test_superuser.id}",
        headers=authenticated_headers
    )
    # Based on current router protection (Depends(get_current_active_superuser))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "The user doesn't have enough privileges" in response.json()["detail"]

# Add more tests:
# - Attempting to update another user's details by a regular user (should be forbidden).
# - Attempting to change superuser status by a non-superuser (should be forbidden).
# - Attempting to change tenant_id by a non-superuser (should be forbidden).
# - Deleting a non-existent user.
