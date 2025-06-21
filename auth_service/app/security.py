from passlib.context import CryptContext
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel

from .config import settings

# Configure passlib for password hashing
# CryptContext is used to hash and verify passwords.
# "bcrypt" is a strong hashing algorithm.
# "auto" will automatically select the default scheme (bcrypt) and handle upgrades.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# Settings model for fastapi-jwt-auth
# This allows AuthJWT to load its configuration from Pydantic settings
# defined in config.py, which in turn can load from .env files.
class AuthJWTSettings(BaseModel):
    authjwt_secret_key: str = settings.AUTHJWT_SECRET_KEY
    authjwt_algorithm: str = settings.AUTHJWT_ALGORITHM
    authjwt_token_location: set[str] = settings.AUTHJWT_TOKEN_LOCATION
    authjwt_cookie_secure: bool = settings.AUTHJWT_COOKIE_SECURE
    authjwt_cookie_samesite: str = settings.AUTHJWT_COOKIE_SAMESITE
    # Add other fastapi-jwt-auth settings from your config.py as needed
    # For example, if using CSRF protection with cookies:
    # authjwt_cookie_csrf_protect: bool = settings.AUTHJWT_COOKIE_CSRF_PROTECT
    # authjwt_csrf_methods: list[str] = settings.AUTHJWT_CSRF_METHODS

# Callback to load settings into AuthJWT
@AuthJWT.load_config
def get_config():
    return AuthJWTSettings()

# Note:
# The actual JWT creation (create_access_token, create_refresh_token)
# and verification (@jwt_required, @jwt_refresh_token_required, get_jwt_subject)
# will be done within the API route handlers using an instance of AuthJWT()
# or by using it as a dependency.

# Example of how to protect an endpoint (will be used in routers):
# from fastapi import Depends, HTTPException, status
# from fastapi_jwt_auth import AuthJWT
# from .schemas import User # Your Pydantic user schema

# async def get_current_user(Authorize: AuthJWT = Depends()) -> User: # Replace User with your actual user model/schema
#     Authorize.jwt_required()
#     user_id = Authorize.get_jwt_subject()
#     # Here you would fetch the user from DB based on user_id
#     # user = await crud_get_user(db, user_id=user_id)
#     # if not user:
#     #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
#     # return user
#     pass # Placeholder for actual user retrieval logic

# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     # if not current_user.is_active:
#     #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
#     # return current_user
#     pass # Placeholder for active check
