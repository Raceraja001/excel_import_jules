from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from .config import settings

# Create an async engine
# NullPool is often recommended for serverless or async environments
# to prevent issues with shared connections across event loops/requests.
# For a traditional server setup, AsyncAdaptedQueuePool (default) might be fine.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for debugging SQL statements
    poolclass=NullPool # Good practice for async, especially with FastAPI
)

# Create a sessionmaker for async sessions
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevents SQLAlchemy from expiring attributes after commit
)

# Base class for declarative models
Base = declarative_base()

# Dependency to get a DB session
async def get_db_session() -> AsyncSession:
    """
    Dependency that provides a database session for a request.
    Ensures the session is closed after the request is finished.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit() # Commit changes if no exceptions occurred
        except Exception:
            await session.rollback() # Rollback in case of an error
            raise
        finally:
            await session.close()

# Function to create all tables (useful for initial setup or tests, use Alembic for production)
async def create_db_and_tables():
    async with engine.begin() as conn:
        # This will create tables based on models imported and registered with Base
        # Make sure all your models are imported somewhere before calling this.
        await conn.run_sync(Base.metadata.create_all)

async def drop_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Example of how to use in an application startup event (optional)
# from fastapi import FastAPI
# app = FastAPI()
# @app.on_event("startup")
# async def on_startup():
#     # Not recommended for production, use migrations instead.
#     # await create_db_and_tables()
#     pass
