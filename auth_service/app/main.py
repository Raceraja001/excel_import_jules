from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException

from .config import settings
from .routers import auth_router, user_router, tenant_router # Import the routers
from .database import create_db_and_tables, drop_db_and_tables # For initial setup/dev only

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Exception handler for AuthJWTException
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# Placeholder for loading JWT settings (already done via security.py and AuthJWT.load_config)
# @AuthJWT.load_config (This is typically done once, e.g., in security.py)
# def get_config():
#     return settings # Assuming your settings object has AUTHJWT_SECRET_KEY etc.
                     # This is now handled by the AuthJWTSettings model in security.py

# --- Event Handlers for Development ---
# In a real application, you would use Alembic for migrations.
# These are for demonstration or quick local setup.

# @app.on_event("startup")
# async def on_startup():
#     # This is dangerous in production. Use Alembic migrations.
#     # Ensure all models are imported so Base.metadata knows about them.
#     # from .models import User, Tenant # noqa
#     # await drop_db_and_tables() # Optional: for a clean slate on each startup during dev
#     # await create_db_and_tables()
#     # print("Database tables created (if they didn't exist).")
#     pass

# @app.on_event("shutdown")
# async def on_shutdown():
#     # Clean up resources if needed
#     pass

# --- Routers ---
app.include_router(auth_router.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(user_router.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(tenant_router.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["Tenants"])


# Basic Health Check / Ping Endpoint
@app.get("/ping", tags=["Health Check"])
async def ping():
    """
    Simple health check endpoint.
    """
    return {"ping": "pong!"}

@app.get(f"{settings.API_V1_STR}/ping", tags=["Health Check V1"])
async def ping_v1():
    """
    Simple health check endpoint under API v1 prefix.
    """
    return {"ping_v1": "pong!"}

# Example of a protected route (will be moved to a router)
# from .schemas import User as UserSchema # Your Pydantic User schema
# from .security import get_current_active_user # Your dependency

# @app.get(f"{settings.API_V1_STR}/users/me", response_model=UserSchema, tags=["Users"])
# async def read_users_me(current_user: UserSchema = Depends(get_current_active_user)):
#    return current_user

if __name__ == "__main__":
    import uvicorn
    # This is for running directly with `python app/main.py`
    # For production, use `uvicorn app.main:app --host 0.0.0.0 --port 8000`
    uvicorn.run(app, host="0.0.0.0", port=8000)
