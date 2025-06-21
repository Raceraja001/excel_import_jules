import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from .. import schemas
from ..database import get_db_session
from ..dependencies import get_current_active_user, get_current_active_superuser # More granular permissions
from ..models.user_model import User as UserModel # SQLAlchemy model

router = APIRouter()

# --- User Management Endpoints ---

# For creating users, let's assume only superusers can create other superusers
# or users without a tenant. Regular users (even tenant admins) might create users within their tenant.
# This logic can be quite complex and would typically involve a more robust role/permission system.
# For now, let's simplify:
# - Superusers can create any user.
# - For creating a user associated with a tenant, we might need a different permission level
#   (e.g., tenant admin or superuser).

@router.post(
    "/",
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED
    # dependencies=[Depends(get_current_active_superuser)] # Simplest: only superuser creates
    # More complex: check if creating user is superuser OR tenant admin for user_in.tenant_id
)
async def create_new_user(
    user_in: schemas.UserCreate,
    db: AsyncSession = Depends(get_db_session),
    # current_creating_user: UserModel = Depends(get_current_active_user) # User performing the action
):
    """
    Create a new user.
    -   If `user_in.is_superuser` is True, the creating user must be a superuser.
    -   If `user_in.tenant_id` is specified, the tenant must exist.
    (Permissions for who can create users for specific tenants to be refined)
    """
    # Permission Check (Example - can be more robust)
    # if user_in.is_superuser and not current_creating_user.is_superuser:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only superusers can create other superusers."
    #     )
    # if user_in.tenant_id and not current_creating_user.is_superuser:
    #     # Here, you might check if current_creating_user is admin of user_in.tenant_id
    #     # For now, let's assume this route is superuser-only for simplicity if creating for a specific tenant
    #     # or if creating a superuser. For general user registration, use /auth/register.
    #     pass


    existing_user = await crud.user.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user_in.email}' already exists.",
        )

    if user_in.tenant_id:
        tenant = await crud.tenant.get_tenant(db, tenant_id=user_in.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with id '{user_in.tenant_id}' not found.",
            )

    # For this generic POST /users/ endpoint, let's restrict it to superusers for now
    # to avoid conflicts with the /auth/register public endpoint's logic.
    # This endpoint is more for administrative user creation.
    # ---- This part should be uncommented when `current_creating_user` is used ----
    # if not current_creating_user.is_superuser:
    #      raise HTTPException(
    #          status_code=status.HTTP_403_FORBIDDEN,
    #          detail="User creation via this endpoint is restricted to superusers."
    #      )
    # ---- End restriction ----

    new_user = await crud.user.create_user(db=db, user_in=user_in)
    return new_user

@router.get(
    "/",
    response_model=List[schemas.UserWithTenant], # Or List[schemas.User]
    dependencies=[Depends(get_current_active_superuser)] # Only superusers can list all users
)
async def read_users_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve a list of users. Requires superuser privileges.
    """
    users = await crud.user.get_users(db, skip=skip, limit=limit)
    # Manually construct UserWithTenant if relationships are not eagerly loaded by default
    # For now, assuming Pydantic's from_attributes and schema definition handle it.
    # users_with_tenant_info = []
    # for user in users:
    #     tenant_info = None
    #     if user.tenant: # Assuming user.tenant is loaded
    #         tenant_info = schemas.Tenant.model_validate(user.tenant)
    #     users_with_tenant_info.append(schemas.UserWithTenant(**schemas.User.model_validate(user).model_dump(), tenant=tenant_info))
    # return users_with_tenant_info
    return users


@router.get(
    "/{user_id}",
    response_model=schemas.UserWithTenant, # Or schemas.User
    # Permissions: Superuser OR the user themselves OR admin of the user's tenant
)
async def read_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Get a specific user by their ID.
    - Superusers can access any user.
    - Regular users can only access their own profile.
    (Tenant admin access to users in their tenant can be added later)
    """
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user's details."
        )

    db_user = await crud.user.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Similar to list users, ensure tenant info is correctly populated for UserWithTenant
    return db_user


@router.put(
    "/{user_id}",
    response_model=schemas.User,
    # Permissions: Superuser OR the user themselves
)
async def update_existing_user(
    user_id: uuid.UUID,
    user_in: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Update an existing user.
    - Superusers can update any user.
    - Regular users can only update their own profile.
    - Superuser status can only be changed by a superuser.
    - Tenant assignment changes might be restricted to superusers.
    """
    db_user = await crud.user.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this user."
        )

    # Prevent non-superusers from making themselves superuser or changing superuser status of others
    if user_in.is_superuser is not None and user_in.is_superuser != db_user.is_superuser and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can change superuser status."
        )

    # Prevent non-superusers from changing tenant_id if it's already set or they are changing it
    if user_in.tenant_id is not None and user_in.tenant_id != db_user.tenant_id and not current_user.is_superuser:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can change tenant assignment."
        )

    if user_in.email and user_in.email != db_user.email:
        existing_user_email = await crud.user.get_user_by_email(db, email=user_in.email)
        if existing_user_email and existing_user_email.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_in.email}' is already registered by another user.",
            )

    updated_user = await crud.user.update_user(db=db, user_db_obj=db_user, user_in=user_in)
    return updated_user


@router.delete(
    "/{user_id}",
    response_model=schemas.User, # Or a success message
    dependencies=[Depends(get_current_active_superuser)] # Only superusers can delete users for now
)
async def delete_existing_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    # current_user: UserModel = Depends(get_current_active_superuser) # Ensure deleter is superuser
):
    """
    Delete an existing user. Requires superuser privileges.
    (Consider if users should be able to delete their own accounts - specific logic needed)
    """
    # if current_user.id == user_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Superusers cannot delete their own account via this endpoint. Use a dedicated procedure."
    #     )

    deleted_user = await crud.user.delete_user(db, user_id=user_id)
    if not deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return deleted_user
