from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "mysql+asyncmy://user:password@localhost:3306/auth_db"

    # JWT Settings from fastapi-jwt-auth
    # Location for tokens: "header" (default), "cookies"
    AUTHJWT_TOKEN_LOCATION: set[str] = {"header"}
    # Algorithm for JWT signing
    AUTHJWT_SECRET_KEY: str = "your-super-secret-key-please-change-it"
    # Options: "HS256", "HS384", "HS512", "ES256", "ES384", "ES512", "RS256", "RS384", "RS512", "PS256", "PS384", "PS512"
    # For symmetric algorithms (HS*), AUTHJWT_SECRET_KEY is used.
    # For asymmetric algorithms (ES*, RS*, PS*), you'll need AUTHJWT_PRIVATE_KEY and AUTHJWT_PUBLIC_KEY.
    AUTHJWT_ALGORITHM: str = "HS256"
    # Configure access token expire time in seconds. Default is 15 minutes.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # Configure refresh token expire time in days. Default is 30 days.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # If using cookies
    AUTHJWT_COOKIE_SECURE: bool = False  # Should be True in production over HTTPS
    AUTHJWT_COOKIE_SAMESITE: str = "lax" # "lax", "strict", "none"
    # AUTHJWT_ACCESS_COOKIE_KEY: str = "access_token_cookie"
    # AUTHJWT_REFRESH_COOKIE_KEY: str = "refresh_token_cookie"
    # AUTHJWT_COOKIE_CSRF_PROTECT: bool = True # If True, set AUTHJWT_CSRF_METHODS and optionally AUTHJWT_CSRF_FIELD_NAME
    # AUTHJWT_CSRF_METHODS: List[str] = ["POST", "PUT", "PATCH", "DELETE"] # Case insensitive

    # API general settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Auth Service"

    # CORS settings (example, adjust as needed)
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:3000"] # Adjust for your frontend

    # For loading .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
