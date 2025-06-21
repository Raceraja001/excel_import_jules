import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from .. import schemas
from ..database import get_db_session
from ..dependencies import get_current_active_superuser # Or a more granular permission dependency
from ..models.tenant_model import Tenant as TenantModel # SQLAlchemy model

router = APIRouter()

# For now, all tenant operations require superuser privileges.
# This can be refined later (e.g., tenant admins can manage their own tenant).

@router.post(
    "/",
    response_model=schemas.Tenant,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_active_superuser)] # Protect endpoint
)
async def create_new_tenant(
    tenant_in: schemas.TenantCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new tenant. Requires superuser privileges.
    """
    existing_tenant = await crud.tenant.get_tenant_by_name(db, name=tenant_in.name)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with name '{tenant_in.name}' already exists.",
        )
    new_tenant = await crud.tenant.create_tenant(db=db, tenant=tenant_in)
    return new_tenant

@router.get(
    "/",
    response_model=List[schemas.Tenant],
    dependencies=[Depends(get_current_active_superuser)] # Protect endpoint
)
async def read_tenants_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve a list of tenants. Requires superuser privileges.
    """
    tenants = await crud.tenant.get_tenants(db, skip=skip, limit=limit)
    return tenants

@router.get(
    "/{tenant_id}",
    response_model=schemas.TenantWithUsers, # Or schemas.Tenant if users list is not needed here
    dependencies=[Depends(get_current_active_superuser)] # Protect endpoint
)
async def read_tenant_by_id(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific tenant by its ID. Requires superuser privileges.
    Includes list of users associated with the tenant.
    """
    db_tenant = await crud.tenant.get_tenant(db, tenant_id=tenant_id)
    if not db_tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    # To include users, ensure the model relationship is loaded, or fetch them separately.
    # SQLAlchemy's default relationship loading might handle this if accessed.
    # For explicit loading with async, it can be more involved if not using default eager loads.
    # For now, assuming the schemas.TenantWithUsers can be populated from db_tenant directly
    # if the relationship 'users' is properly configured and accessed.
    # Let's try to populate it. This depends on how Pydantic from_attributes works with lazy loaded relationships.
    # A more robust way for async is to explicitly load relationships if needed:
    # from sqlalchemy.orm import selectinload
    # result = await db.execute(
    #     select(TenantModel).options(selectinload(TenantModel.users)).filter(TenantModel.id == tenant_id)
    # )
    # db_tenant = result.scalars().first()

    return db_tenant # FastAPI will try to map this to TenantWithUsers

@router.put(
    "/{tenant_id}",
    response_model=schemas.Tenant,
    dependencies=[Depends(get_current_active_superuser)] # Protect endpoint
)
async def update_existing_tenant(
    tenant_id: uuid.UUID,
    tenant_in: schemas.TenantUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing tenant. Requires superuser privileges.
    """
    db_tenant = await crud.tenant.get_tenant(db, tenant_id=tenant_id)
    if not db_tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if tenant_in.name:
        existing_tenant_with_name = await crud.tenant.get_tenant_by_name(db, name=tenant_in.name)
        if existing_tenant_with_name and existing_tenant_with_name.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant name '{tenant_in.name}' is already in use by another tenant.",
            )

    updated_tenant = await crud.tenant.update_tenant(
        db=db, tenant_db_obj=db_tenant, tenant_in=tenant_in
    )
    return updated_tenant

@router.delete(
    "/{tenant_id}",
    response_model=schemas.Tenant, # Or perhaps a success message
    dependencies=[Depends(get_current_active_superuser)] # Protect endpoint
)
async def delete_existing_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete an existing tenant. Requires superuser privileges.
    This will also delete associated users due to cascade settings in the model.
    """
    deleted_tenant = await crud.tenant.delete_tenant(db, tenant_id=tenant_id)
    if not deleted_tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return deleted_tenant
