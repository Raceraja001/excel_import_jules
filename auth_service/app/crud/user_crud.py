import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user_model import User
from ..schemas.user_schema import UserCreate, UserUpdate
from ..security import get_password_hash


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """
    Creates a new user in the database.
    - Hashes the password before storing.
    - Associates with a tenant if tenant_id is provided in UserCreate schema.
    """
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        is_active=user_in.is_active if user_in.is_active is not None else True,
        is_superuser=user_in.is_superuser if user_in.is_superuser is not None else False,
        tenant_id=user_in.tenant_id
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """
    Retrieves a user by their ID.
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Retrieves a user by their email address.
    """
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Retrieves a list of users with pagination.
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

async def update_user(
    db: AsyncSession, user_db_obj: User, user_in: UserUpdate
) -> User:
    """
    Updates an existing user.
    - user_db_obj is the user object fetched from the DB.
    - user_in contains the new data.
    - Hashes the password if a new one is provided.
    """
    update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        user_db_obj.hashed_password = hashed_password
        del update_data["password"] # Don't try to set it directly

    for field, value in update_data.items():
        setattr(user_db_obj, field, value)

    db.add(user_db_obj) # Not strictly necessary if already in session and modified
    await db.commit()
    await db.refresh(user_db_obj)
    return user_db_obj

async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """
    Deletes a user by their ID.
    Returns the deleted user object or None if not found.
    """
    db_user = await get_user(db, user_id=user_id)
    if db_user:
        await db.delete(db_user)
        await db.commit()
        return db_user
    return None

async def activate_user(db: AsyncSession, user: User) -> User:
    """
    Activates a user.
    """
    user.is_active = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def deactivate_user(db: AsyncSession, user: User) -> User:
    """
    Deactivates a user.
    """
    user.is_active = False
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
