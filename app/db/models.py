import uuid
from sqlalchemy import ForeignKey, String, UUID, Boolean, Enum
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


from app.schemas import UserRoles, UserActionType


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role: Mapped[Enum] = mapped_column(
        Enum(UserRoles), default=UserRoles.USER, nullable=False
    )
    ssh_username: Mapped[str] = mapped_column(String(32), nullable=True)
    is_active: Mapped[Boolean] = mapped_column(Boolean, default=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)


class UsersActivityLog(Base):
    __tablename__ = "users_activity_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    action: Mapped[Enum] = mapped_column(Enum(UserActionType), nullable=False)
    server: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)

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

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_action_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users_activity_log.id", ondelete="CASCADE"),
        nullable=False,
    )


class DeleteZonemasterLog(UserActionLogBase):
    __tablename__ = "zone_master_delete_log"

    current_zone_master: Mapped[str] = mapped_column(String, nullable=False)
    user_action = relationship(
        "UsersActivityLog", back_populates="dns_zone_delete_logs"
    )


class SetZoneMasterLog(UserActionLogBase):
    __tablename__ = "zone_master_set_log"

    current_zone_master: Mapped[str] = mapped_column(String)
    target_zone_master: Mapped[str] = mapped_column(String, nullable=False)
    domain = mapped_column(String, nullable=False)
    user_action = relationship(
        "UsersActivityLog", back_populates="dns_set_zone_master_logs"
    )


class GetZoneMasterLog(UserActionLogBase):
    __tablename__ = "zone_master_get_log"

    domain: Mapped[str] = mapped_column(String, nullable=False)
    user_action = relationship(
        "UsersActivityLog", back_populates="dns_get_zone_master_logs"
    )
