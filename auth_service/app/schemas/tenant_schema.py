import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Forward declaration for User schema to handle circular dependencies
class User(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Base properties for Tenant
class TenantBase(BaseModel):
    name: str

# Properties to receive via API on creation
class TenantCreate(TenantBase):
    pass

# Properties to receive via API on update
class TenantUpdate(TenantBase):
    name: Optional[str] = None # All fields optional on update

# Properties shared by models stored in DB
class TenantInDBBase(TenantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Additional properties to return to client
class Tenant(TenantInDBBase):
    pass

# Additional properties stored in DB
class TenantInDB(TenantInDBBase):
    pass

# Schema for returning a tenant with its users
class TenantWithUsers(Tenant):
    users: List[User] = []

# Update User schema to include Tenant information if needed, or define a UserWithTenant schema.
# This is to resolve the circular dependency by updating the forward-referenced model.
# User.model_rebuild() # Not strictly necessary here as Tenant is defined before User in this file context,
                     # but good practice if User was defined in a separate file and imported.
                     # Actually, this is for when User itself contains Tenant.
                     # For TenantWithUsers, the User schema is self-contained enough.
