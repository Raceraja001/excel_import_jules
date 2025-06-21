import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tenant_model import Tenant
from ..schemas.tenant_schema import TenantCreate, TenantUpdate


async def create_tenant(db: AsyncSession, tenant: TenantCreate) -> Tenant:
    """
    Creates a new tenant in the database.
    """
    db_tenant = Tenant(name=tenant.name)
    db.add(db_tenant)
    await db.commit()
    await db.refresh(db_tenant)
    return db_tenant

async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[Tenant]:
    """
    Retrieves a tenant by its ID.
    """
    result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
    return result.scalars().first()

async def get_tenant_by_name(db: AsyncSession, name: str) -> Optional[Tenant]:
    """
    Retrieves a tenant by its name.
    """
    result = await db.execute(select(Tenant).filter(Tenant.name == name))
    return result.scalars().first()

async def get_tenants(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Tenant]:
    """
    Retrieves a list of tenants with pagination.
    """
    result = await db.execute(select(Tenant).offset(skip).limit(limit))
    return result.scalars().all()

async def update_tenant(
    db: AsyncSession, tenant_db_obj: Tenant, tenant_in: TenantUpdate
) -> Tenant:
    """
    Updates an existing tenant.
    Assumes tenant_db_obj is a persisted Tenant model instance.
    """
    if tenant_in.name is not None:
        tenant_db_obj.name = tenant_in.name

    # sqlalchemy tracks changes, so just need to add and commit
    db.add(tenant_db_obj) # Not strictly necessary if already in session and modified
    await db.commit()
    await db.refresh(tenant_db_obj)
    return tenant_db_obj

async def delete_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[Tenant]:
    """
    Deletes a tenant by its ID.
    Returns the deleted tenant object or None if not found.
    """
    db_tenant = await get_tenant(db, tenant_id=tenant_id)
    if db_tenant:
        await db.delete(db_tenant)
        await db.commit()
        return db_tenant
    return None
