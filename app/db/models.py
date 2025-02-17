import uuid
from sqlalchemy import Column, ForeignKey, String, UUID, Integer, Boolean, Enum
from sqlalchemy.orm import relationship, DeclarativeBase
from app.schemas import UserRoles


class Base(DeclarativeBase):
    pass


# Shared properties
class UserBase(Base):
    __abstract__ = True

    email = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRoles), default=UserRoles.USER, nullable=False)
    ssh_username = Column(String(32), nullable=True)


class User(UserBase):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hashed_password = Column(String, nullable=False)


class UsersActivityLog(Base):
    __tablename__ = "users_activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    action = Column(String, nullable=False)
    server = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)

    dns_zone_delete_logs = relationship(
        "DeleteZonemasterLog", back_populates="user_action", cascade="all, delete"
    )
    dns_set_zone_master_logs = relationship(
        "SetZoneMasterLog", back_populates="user_action", cascade="all, delete"
    )
    dns_get_zone_master_logs = relationship(
        "GetZoneMasterLog", back_populates="user_action", cascade="all, delete"
    )


class UserActionLogBase(Base):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_action_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_activity_log.id", ondelete="CASCADE"),
        nullable=False,
    )


class DeleteZonemasterLog(UserActionLogBase):
    __tablename__ = "zone_master_delete_log"

    current_zone_master = Column(String, nullable=False)
    user_action = relationship(
        "UsersActivityLog", back_populates="dns_zone_delete_logs"
    )


class SetZoneMasterLog(UserActionLogBase):
    __tablename__ = "zone_master_set_log"

    current_zone_master = Column(String)
    target_zone_master = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    user_action = relationship(
        "UsersActivityLog", back_populates="dns_set_zone_master_logs"
    )


class GetZoneMasterLog(UserActionLogBase):
    __tablename__ = "zone_master_get_log"

    domain = Column(String, nullable=False)
    user_action = relationship(
        "UsersActivityLog", back_populates="dns_get_zone_master_logs"
    )
