import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # For form data login
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_jwt_auth import AuthJWT

from .. import crud
from .. import schemas
from ..database import get_db_session
from ..config import settings
from ..security import verify_password #, get_password_hash (create_user in crud handles hashing)
from ..models.user_model import User as UserModel # To type hint current_user

router = APIRouter()

# --- Helper to create tokens ---
def _create_tokens(Authorize: AuthJWT, subject: str | uuid.UUID) -> schemas.Token:
    access_token = Authorize.create_access_token(
        subject=str(subject),
        expires_time=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = Authorize.create_refresh_token(
        subject=str(subject),
        expires_time=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


# --- Registration ---
@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register_new_user(
    user_in: schemas.UserCreate, # UserCreate now includes optional tenant_id
    db: AsyncSession = Depends(get_db_session),
    Authorize: AuthJWT = Depends() # Added for consistency, though not strictly used for token creation here
):
    """
    Register a new user.
    If tenant_id is provided in user_in and exists, user is assigned to it.
    If tenant_id is not provided, a new tenant could potentially be created,
    or registration could be rejected depending on business rules.
    For now, we assume tenant_id is optional and user can be created without one (e.g. superuser)
    or must be provided if the user is tenant-specific.

    Simplified: User is created. If user_in.tenant_id is provided, it's used.
    More complex logic (like auto-creating a tenant) can be added here or in a service layer.
    """
    db_user = await crud.user.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    if user_in.tenant_id:
        db_tenant = await crud.tenant.get_tenant(db, tenant_id=user_in.tenant_id)
        if not db_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with id {user_in.tenant_id} not found."
            )

    new_user = await crud.user.create_user(db=db, user_in=user_in)
    # Optionally, log in the user immediately and return tokens
    # For now, just return user details. They can log in separately.
    return new_user


# --- Login ---
@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), # username is email
    db: AsyncSession = Depends(get_db_session),
    Authorize: AuthJWT = Depends()
):
    """
    Authenticate user and return JWT tokens.
    Uses OAuth2PasswordRequestForm, so client should send 'username' (for email) and 'password'.
    """
    user = await crud.user.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}, # Standard for 401
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access and refresh tokens
    return _create_tokens(Authorize, user.id)


# --- Refresh Token ---
@router.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(
    Authorize: AuthJWT = Depends(),
    # db: AsyncSession = Depends(get_db_session) # Not strictly needed if not checking user status on refresh
):
    """
    Refresh an access token using a refresh token.
    The refresh token must be present (e.g., in headers or cookies as configured).
    """
    Authorize.jwt_refresh_token_required()
    current_user_id = Authorize.get_jwt_subject()
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    # Optionally: check if user still exists and is active
    # user = await crud.user.get_user(db, user_id=uuid.UUID(current_user_id))
    # if not user or not user.is_active:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active or found")

    # Create new access token (refresh token remains the same or can be reissued)
    new_access_token = Authorize.create_access_token(
        subject=current_user_id, # Must be a string
        expires_time=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # Return new access token, potentially with the existing refresh token or a new one
    return schemas.Token(access_token=new_access_token, refresh_token=Authorize.get_raw_jwt()['jti']) # Or however you manage refresh tokens


from ..dependencies import get_current_active_user # Import the dependency


@router.get("/me", response_model=schemas.User) # Use the Pydantic schema for response
async def read_users_me(
    current_user: UserModel = Depends(get_current_active_user) # Use the dependency from dependencies.py
):
    """
    Get current authenticated user's details.
    """
    return current_user # FastAPI will convert UserModel to schemas.User based on response_model


# TODO: Add /logout endpoint if using denylist for tokens or if client needs explicit logout
# @router.post("/logout")
# async def logout(Authorize: AuthJWT = Depends()):
#     # If using a denylist, add the token JTI to it.
#     # Authorize.jwt_required() # or refresh token required depending on strategy
#     # jti = Authorize.get_raw_jwt()['jti']
#     # await add_to_denylist(jti, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) # Example
#     return {"msg":"Successfully logged out"}
