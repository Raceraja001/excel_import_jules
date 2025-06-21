import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID # Generic UUID type

from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False) # For global admin, if needed

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True) # Nullable if a user can exist without a tenant (e.g. superuser)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="users")

    # Add roles relationship if you have a Role model
    # roles = relationship("Role", secondary=user_roles_table, back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
