import uuid
from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None # Include if you are using refresh tokens
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    # 'sub' is standard for subject (user identifier)
    # For fastapi-jwt-auth, the subject is retrieved by get_jwt_subject()
    # It can be any type, but usually string or UUID.
    sub: uuid.UUID | str # Can be user ID
    # You can add other custom claims here if needed
    # type: Optional[str] = None # e.g. "access" or "refresh" if you use one payload for both
    # fresh: Optional[bool] = False
    # tenant_id: Optional[uuid.UUID] = None # Example custom claim

class RefreshToken(BaseModel):
    refresh_token: str

# This schema might be used by fastapi-jwt-auth internally or for your own type hinting
# when dealing with decoded token data.
class TokenData(BaseModel):
    # This depends on what you store in your token.
    # If you followed fastapi-jwt-auth defaults, 'sub' is the primary one.
    # If you add custom claims like 'tenant_id' to the token, include them here.
    sub: Optional[str | uuid.UUID] = None
    # tenant_id: Optional[str | uuid.UUID] = None # Example if you add tenant_id to token payload
    exp: Optional[int] = None # Expiration time
    # iat: Optional[int] = None # Issued at
    # nbf: Optional[int] = None # Not before
    # jti: Optional[str] = None # JWT ID

# If you are using CSRF protection with cookies
class CsrfToken(BaseModel):
    csrf_token: str
