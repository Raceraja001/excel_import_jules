import pytest
from httpx import AsyncClient
from fastapi import status
import uuid

from app.config import settings
from app.schemas import TenantCreate, TenantUpdate
from app.models import Tenant as TenantModel, User as UserModel # SQLAlchemy models
from sqlalchemy.ext.asyncio import AsyncSession

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Test Tenant Creation ---
async def test_create_new_tenant_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    db: AsyncSession # For verification
):
    tenant_name = "SuperCreated Tenant LLC"
    tenant_data_in = {"name": tenant_name}

    response = await async_client.post(
        f"{settings.API_V1_STR}/tenants/",
        json=tenant_data_in,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_tenant = response.json()
    assert created_tenant["name"] == tenant_name
    assert "id" in created_tenant

    # Verify in DB
    from app.crud import tenant as tenant_crud
    db_tenant = await tenant_crud.get_tenant_by_name(db, name=tenant_name)
    assert db_tenant is not None
    assert db_tenant.name == tenant_name

async def test_create_tenant_existing_name_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel # Fixture for an existing tenant
):
    tenant_data_in = {"name": test_tenant.name} # Attempt to create with same name
    response = await async_client.post(
        f"{settings.API_V1_STR}/tenants/",
        json=tenant_data_in,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Tenant with name '{test_tenant.name}' already exists" in response.json()["detail"]

async def test_create_tenant_by_regular_user_forbidden(
    async_client: AsyncClient,
    authenticated_headers: dict # Regular user's headers
):
    tenant_data_in = {"name": "UserCreated Tenant Ltd."}
    response = await async_client.post(
        f"{settings.API_V1_STR}/tenants/",
        json=tenant_data_in,
        headers=authenticated_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "The user doesn't have enough privileges" in response.json()["detail"]


# --- Test List Tenants ---
async def test_read_tenants_list_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel # Ensure at least one tenant exists
):
    response = await async_client.get(f"{settings.API_V1_STR}/tenants/", headers=superuser_authenticated_headers)
    assert response.status_code == status.HTTP_200_OK
    tenants_list = response.json()
    assert isinstance(tenants_list, list)
    assert len(tenants_list) >= 1

    names_in_response = [t["name"] for t in tenants_list]
    assert test_tenant.name in names_in_response

async def test_read_tenants_list_by_regular_user_forbidden(
    async_client: AsyncClient,
    authenticated_headers: dict
):
    response = await async_client.get(f"{settings.API_V1_STR}/tenants/", headers=authenticated_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Test Get Specific Tenant ---
async def test_read_tenant_by_id_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel,
    test_user: UserModel # A user associated with test_tenant from fixtures
):
    # Ensure test_user is actually associated with test_tenant (fixture setup dependent)
    assert test_user.tenant_id == test_tenant.id

    response = await async_client.get(
        f"{settings.API_V1_STR}/tenants/{test_tenant.id}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    tenant_details = response.json()
    assert tenant_details["name"] == test_tenant.name
    assert tenant_details["id"] == str(test_tenant.id)

    # Check if users are included (TenantWithUsers schema)
    assert "users" in tenant_details
    assert isinstance(tenant_details["users"], list)
    user_ids_in_tenant_details = [u["id"] for u in tenant_details["users"]]
    assert str(test_user.id) in user_ids_in_tenant_details


async def test_read_nonexistent_tenant_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict
):
    non_existent_uuid = uuid.uuid4()
    response = await async_client.get(
        f"{settings.API_V1_STR}/tenants/{non_existent_uuid}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenant not found" in response.json()["detail"]


# --- Test Update Tenant ---
async def test_update_tenant_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel,
    db: AsyncSession
):
    updated_name = "Updated Global Corp"
    update_data = {"name": updated_name}

    response = await async_client.put(
        f"{settings.API_V1_STR}/tenants/{test_tenant.id}",
        json=update_data,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    updated_tenant_json = response.json()
    assert updated_tenant_json["name"] == updated_name

    await db.refresh(test_tenant) # Refresh from DB
    assert test_tenant.name == updated_name

async def test_update_tenant_name_to_existing_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel, # Target tenant for update
    db: AsyncSession
):
    # Create another tenant to cause a name conflict
    conflicting_tenant_name = "Conflicting Name LLC"
    from app.crud.tenant_crud import create_tenant as crud_create_tenant
    from app.schemas.tenant_schema import TenantCreate as SchemaTenantCreate
    _ = await crud_create_tenant(db, SchemaTenantCreate(name=conflicting_tenant_name))

    update_data = {"name": conflicting_tenant_name} # Try to update test_tenant's name
    response = await async_client.put(
        f"{settings.API_V1_STR}/tenants/{test_tenant.id}",
        json=update_data,
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Tenant name '{conflicting_tenant_name}' is already in use" in response.json()["detail"]


# --- Test Delete Tenant ---
async def test_delete_tenant_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict,
    test_tenant: TenantModel,
    test_user: UserModel, # User associated with this tenant
    db: AsyncSession
):
    tenant_id_to_delete = test_tenant.id
    user_id_associated = test_user.id # This user should be deleted by cascade

    response = await async_client.delete(
        f"{settings.API_V1_STR}/tenants/{tenant_id_to_delete}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_200_OK
    deleted_tenant_json = response.json()
    assert deleted_tenant_json["id"] == str(tenant_id_to_delete)

    # Verify tenant is deleted
    from app.crud import tenant as tenant_crud
    db_tenant = await tenant_crud.get_tenant(db, tenant_id=tenant_id_to_delete)
    assert db_tenant is None

    # Verify associated user is deleted (due to cascade="all, delete-orphan")
    from app.crud import user as user_crud
    db_user = await user_crud.get_user(db, user_id=user_id_associated)
    assert db_user is None

async def test_delete_nonexistent_tenant_by_superuser(
    async_client: AsyncClient,
    superuser_authenticated_headers: dict
):
    non_existent_uuid = uuid.uuid4()
    response = await async_client.delete(
        f"{settings.API_V1_STR}/tenants/{non_existent_uuid}",
        headers=superuser_authenticated_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenant not found" in response.json()["detail"]
