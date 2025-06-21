import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

# Forward declaration for Tenant schema to handle circular dependencies
class Tenant(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Base properties for User
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    tenant_id: Optional[uuid.UUID] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    email: Optional[EmailStr] = None # Allow email update
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    tenant_id: Optional[uuid.UUID] = None


# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Additional properties to return to client (never include password)
class User(UserInDBBase):
    pass

# Schema for returning a user with tenant details
class UserWithTenant(User):
    tenant: Optional[Tenant] = None


# Additional properties stored in DB (including hashed_password)
class UserInDB(UserInDBBase):
    hashed_password: str


# Update Tenant schema to include User information if needed.
# This is to resolve the circular dependency.
# Tenant.model_rebuild() # Not strictly necessary here as User is defined before Tenant in this file context,
                      # but good practice if Tenant was defined in a separate file and imported.
                      # Actually, this is for when Tenant itself contains User.
                      # For UserWithTenant, the Tenant schema is self-contained enough.
