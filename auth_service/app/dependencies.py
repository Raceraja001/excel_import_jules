import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_jwt_auth import AuthJWT

from .database import get_db_session
from . import crud
from .models.user_model import User as UserModel # SQLAlchemy model
from .schemas.user_schema import User as UserSchema # Pydantic schema for response type hint if needed

# Dependency to get the current user from JWT
async def get_current_user(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db_session)
) -> UserModel: # Return the SQLAlchemy model instance
    """
    Dependency to get current user from JWT.
    1. Requires JWT token.
    2. Extracts user ID (subject) from token.
    3. Fetches user from database.
    Raises HTTPException if token is invalid, user not found, or other issues.
    """
    try:
        Authorize.jwt_required()
        user_id_str = Authorize.get_jwt_subject()
    except Exception as e: # Catching generic AuthJWTException or others
        # Log the exception e if needed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token"
        )

    user = await crud.user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# Dependency to get the current active user
async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Dependency to get current active user.
    Checks if the user returned by get_current_user is active.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# Dependency to get the current active superuser
async def get_current_active_superuser(
    current_user: UserModel = Depends(get_current_active_user)
) -> UserModel:
    """
    Dependency to get current active superuser.
    Checks if the user is active and a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

# Example of a more complex permission: Tenant Admin or Superuser
# async def get_tenant_admin_or_superuser(
#     current_user: UserModel = Depends(get_current_active_user),
#     # tenant_id: uuid.UUID = Path(...) # If tenant_id is in path
# ) -> UserModel:
#     """
#     Ensures the current user is either a superuser or an admin for a specific tenant.
#     This would require more logic, potentially checking a roles table or a flag on the user-tenant link.
#     For now, this is a placeholder for future role-based access control (RBAC).
#     """
#     # if current_user.is_superuser:
#     #     return current_user
#     #
#     # is_tenant_admin = await check_if_user_is_admin_for_tenant(db, user_id=current_user.id, tenant_id=tenant_id)
#     # if not is_tenant_admin:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_403_FORBIDDEN,
#     #         detail="User is not an admin for this tenant"
#     #     )
#     return current_user # Placeholder - for now, just returns active user if not superuser
